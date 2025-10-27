"""
Challenge 3 Deliverable: User-Centric Dashboards
Role-specific interfaces for data scientists, analysts, and business users with customizable views
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timezone
from abc import ABC, abstractmethod

class DashboardWidget(Enum):
    """Available dashboard widgets"""
    FIRE_MAP = "fire_map"
    WEATHER_CHART = "weather_chart"
    SENSOR_STATUS = "sensor_status"
    ALERT_PANEL = "alert_panel"
    DATA_METRICS = "data_metrics"
    ANALYSIS_RESULTS = "analysis_results"
    QUICK_STATS = "quick_stats"
    RECENT_ACTIVITY = "recent_activity"
    FORECAST_PANEL = "forecast_panel"
    COMPLIANCE_REPORT = "compliance_report"

class FilterType(Enum):
    """Dashboard filter types"""
    DATE_RANGE = "date_range"
    GEOGRAPHIC_AREA = "geographic_area"
    DATA_SOURCE = "data_source"
    CONFIDENCE_LEVEL = "confidence_level"
    FIRE_SIZE = "fire_size"
    WEATHER_CONDITIONS = "weather_conditions"

@dataclass
class DashboardFilter:
    """Dashboard filter configuration"""
    filter_id: str
    filter_type: FilterType
    label: str
    default_value: Any
    options: Optional[List[Any]] = None
    is_required: bool = False

@dataclass
class WidgetConfiguration:
    """Widget configuration for dashboard"""
    widget_id: str
    widget_type: DashboardWidget
    title: str
    position: Dict[str, int]  # x, y, width, height
    data_source: str
    refresh_interval: int  # seconds
    filters: List[str]
    custom_settings: Dict[str, Any]

@dataclass
class DashboardLayout:
    """Complete dashboard layout definition"""
    dashboard_id: str
    name: str
    description: str
    user_role: str
    widgets: List[WidgetConfiguration]
    filters: List[DashboardFilter]
    default_view: Dict[str, Any]
    is_customizable: bool

class BaseDashboard(ABC):
    """Base class for all user dashboards"""

    def __init__(self, user_id: str, user_role: str):
        self.user_id = user_id
        self.user_role = user_role
        self.layout = self._create_default_layout()
        self.active_filters = {}
        self.custom_settings = {}

    @abstractmethod
    def _create_default_layout(self) -> DashboardLayout:
        """Create the default layout for this dashboard type"""
        pass

    def apply_filter(self, filter_id: str, value: Any):
        """Apply a filter to the dashboard"""
        self.active_filters[filter_id] = value

    def get_filtered_data(self, widget_id: str) -> Dict[str, Any]:
        """Get filtered data for a specific widget"""
        # This would integrate with the data clearing house
        # For now, return sample data
        return self._generate_sample_data(widget_id)

    def customize_widget(self, widget_id: str, settings: Dict[str, Any]):
        """Customize widget settings"""
        for widget in self.layout.widgets:
            if widget.widget_id == widget_id:
                widget.custom_settings.update(settings)
                break

    def save_layout(self) -> Dict[str, Any]:
        """Save current dashboard layout"""
        return asdict(self.layout)

    def _generate_sample_data(self, widget_id: str) -> Dict[str, Any]:
        """Generate sample data for demonstration"""
        return {
            "widget_id": widget_id,
            "data": f"Sample data for {widget_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filters_applied": self.active_filters
        }

class DataScientistDashboard(BaseDashboard):
    """Advanced dashboard for data scientists with research and analysis tools"""

    def _create_default_layout(self) -> DashboardLayout:
        """Create data scientist specific layout"""
        filters = [
            DashboardFilter(
                filter_id="date_range",
                filter_type=FilterType.DATE_RANGE,
                label="Analysis Period",
                default_value={"start": "2024-01-01", "end": "2024-12-31"},
                is_required=True
            ),
            DashboardFilter(
                filter_id="geographic_area",
                filter_type=FilterType.GEOGRAPHIC_AREA,
                label="Study Area",
                default_value="california",
                options=["california", "northern_ca", "southern_ca", "custom_polygon"]
            ),
            DashboardFilter(
                filter_id="data_sources",
                filter_type=FilterType.DATA_SOURCE,
                label="Data Sources",
                default_value=["nasa_firms", "noaa_weather", "iot_sensors"],
                options=["nasa_firms", "noaa_weather", "iot_sensors", "satellite_imagery", "historical_data"]
            ),
            DashboardFilter(
                filter_id="confidence_threshold",
                filter_type=FilterType.CONFIDENCE_LEVEL,
                label="Minimum Confidence",
                default_value=70,
                options=list(range(0, 101, 10))
            )
        ]

        widgets = [
            WidgetConfiguration(
                widget_id="fire_analysis_map",
                widget_type=DashboardWidget.FIRE_MAP,
                title="Multi-Source Fire Detection Analysis",
                position={"x": 0, "y": 0, "width": 8, "height": 6},
                data_source="integrated_fire_data",
                refresh_interval=300,
                filters=["date_range", "geographic_area", "confidence_threshold"],
                custom_settings={
                    "map_type": "satellite",
                    "overlay_layers": ["fire_detections", "weather_stations", "iot_sensors"],
                    "heat_map": True,
                    "clustering": True
                }
            ),
            WidgetConfiguration(
                widget_id="statistical_analysis",
                widget_type=DashboardWidget.ANALYSIS_RESULTS,
                title="Statistical Analysis Results",
                position={"x": 8, "y": 0, "width": 4, "height": 3},
                data_source="analysis_engine",
                refresh_interval=600,
                filters=["date_range", "geographic_area"],
                custom_settings={
                    "analysis_types": ["correlation", "trend", "regression", "clustering"],
                    "visualization": "advanced_charts",
                    "export_formats": ["csv", "json", "python_notebook"]
                }
            ),
            WidgetConfiguration(
                widget_id="data_quality_metrics",
                widget_type=DashboardWidget.DATA_METRICS,
                title="Data Quality and Completeness",
                position={"x": 8, "y": 3, "width": 4, "height": 3},
                data_source="data_quality_service",
                refresh_interval=900,
                filters=["data_sources"],
                custom_settings={
                    "metrics": ["completeness", "accuracy", "timeliness", "consistency"],
                    "alerts": True,
                    "historical_trends": True
                }
            ),
            WidgetConfiguration(
                widget_id="weather_correlation",
                widget_type=DashboardWidget.WEATHER_CHART,
                title="Weather-Fire Correlation Analysis",
                position={"x": 0, "y": 6, "width": 6, "height": 4},
                data_source="weather_fire_analysis",
                refresh_interval=300,
                filters=["date_range", "geographic_area"],
                custom_settings={
                    "variables": ["temperature", "humidity", "wind_speed", "precipitation"],
                    "correlation_methods": ["pearson", "spearman", "kendall"],
                    "visualization": "heatmap_matrix"
                }
            ),
            WidgetConfiguration(
                widget_id="model_results",
                widget_type=DashboardWidget.ANALYSIS_RESULTS,
                title="Predictive Model Results",
                position={"x": 6, "y": 6, "width": 6, "height": 4},
                data_source="ml_models",
                refresh_interval=1800,
                filters=["date_range", "geographic_area"],
                custom_settings={
                    "models": ["fire_risk", "spread_prediction", "weather_forecast"],
                    "accuracy_metrics": True,
                    "feature_importance": True,
                    "model_comparison": True
                }
            )
        ]

        return DashboardLayout(
            dashboard_id="data_scientist_main",
            name="Data Scientist Research Dashboard",
            description="Advanced analytics and research tools for fire behavior analysis",
            user_role="data_scientist",
            widgets=widgets,
            filters=filters,
            default_view={
                "zoom_level": 7,
                "center_lat": 37.5,
                "center_lon": -119.5,
                "time_window": "last_30_days"
            },
            is_customizable=True
        )

class AnalystDashboard(BaseDashboard):
    """Operational dashboard for fire analysts with real-time monitoring"""

    def _create_default_layout(self) -> DashboardLayout:
        """Create analyst specific layout"""
        filters = [
            DashboardFilter(
                filter_id="time_window",
                filter_type=FilterType.DATE_RANGE,
                label="Time Window",
                default_value="last_24_hours",
                options=["last_hour", "last_6_hours", "last_24_hours", "last_week", "custom"]
            ),
            DashboardFilter(
                filter_id="alert_level",
                filter_type=FilterType.CONFIDENCE_LEVEL,
                label="Alert Level",
                default_value="all",
                options=["critical", "high", "medium", "low", "all"]
            ),
            DashboardFilter(
                filter_id="region",
                filter_type=FilterType.GEOGRAPHIC_AREA,
                label="Operational Region",
                default_value="all_regions",
                options=["northern", "central", "southern", "all_regions"]
            )
        ]

        widgets = [
            WidgetConfiguration(
                widget_id="live_fire_map",
                widget_type=DashboardWidget.FIRE_MAP,
                title="Live Fire Detection Monitor",
                position={"x": 0, "y": 0, "width": 9, "height": 7},
                data_source="real_time_fires",
                refresh_interval=60,
                filters=["time_window", "alert_level", "region"],
                custom_settings={
                    "real_time": True,
                    "auto_refresh": True,
                    "incident_details": True,
                    "response_units": True
                }
            ),
            WidgetConfiguration(
                widget_id="alert_panel",
                widget_type=DashboardWidget.ALERT_PANEL,
                title="Active Alerts",
                position={"x": 9, "y": 0, "width": 3, "height": 4},
                data_source="alert_system",
                refresh_interval=30,
                filters=["alert_level", "region"],
                custom_settings={
                    "priority_sorting": True,
                    "auto_escalation": True,
                    "acknowledgment": True
                }
            ),
            WidgetConfiguration(
                widget_id="sensor_status",
                widget_type=DashboardWidget.SENSOR_STATUS,
                title="IoT Sensor Network Status",
                position={"x": 9, "y": 4, "width": 3, "height": 3},
                data_source="iot_monitoring",
                refresh_interval=120,
                filters=["region"],
                custom_settings={
                    "health_indicators": True,
                    "connectivity_status": True,
                    "maintenance_alerts": True
                }
            ),
            WidgetConfiguration(
                widget_id="weather_conditions",
                widget_type=DashboardWidget.WEATHER_CHART,
                title="Current Weather Conditions",
                position={"x": 0, "y": 7, "width": 6, "height": 3},
                data_source="current_weather",
                refresh_interval=180,
                filters=["region"],
                custom_settings={
                    "critical_indicators": ["temperature", "humidity", "wind_speed"],
                    "fire_weather_index": True,
                    "forecasts": True
                }
            ),
            WidgetConfiguration(
                widget_id="incident_summary",
                widget_type=DashboardWidget.QUICK_STATS,
                title="24-Hour Incident Summary",
                position={"x": 6, "y": 7, "width": 6, "height": 3},
                data_source="incident_statistics",
                refresh_interval=300,
                filters=["time_window", "region"],
                custom_settings={
                    "key_metrics": ["new_fires", "active_fires", "acres_burned", "resources_deployed"],
                    "trend_indicators": True
                }
            )
        ]

        return DashboardLayout(
            dashboard_id="analyst_operational",
            name="Fire Analyst Operational Dashboard",
            description="Real-time monitoring and incident response coordination",
            user_role="analyst",
            widgets=widgets,
            filters=filters,
            default_view={
                "zoom_level": 6,
                "center_lat": 37.5,
                "center_lon": -119.5,
                "time_window": "last_24_hours"
            },
            is_customizable=True
        )

class BusinessUserDashboard(BaseDashboard):
    """Executive dashboard for business users with high-level summaries"""

    def _create_default_layout(self) -> DashboardLayout:
        """Create business user specific layout"""
        filters = [
            DashboardFilter(
                filter_id="reporting_period",
                filter_type=FilterType.DATE_RANGE,
                label="Reporting Period",
                default_value="current_month",
                options=["current_week", "current_month", "current_quarter", "current_year", "custom"]
            ),
            DashboardFilter(
                filter_id="organizational_unit",
                filter_type=FilterType.GEOGRAPHIC_AREA,
                label="Organizational Unit",
                default_value="statewide",
                options=["statewide", "region_1", "region_2", "region_3", "specific_unit"]
            )
        ]

        widgets = [
            WidgetConfiguration(
                widget_id="executive_summary",
                widget_type=DashboardWidget.QUICK_STATS,
                title="Executive Summary",
                position={"x": 0, "y": 0, "width": 12, "height": 2},
                data_source="executive_metrics",
                refresh_interval=1800,
                filters=["reporting_period", "organizational_unit"],
                custom_settings={
                    "kpis": ["total_incidents", "response_time", "acres_protected", "cost_savings"],
                    "comparison_periods": True,
                    "trend_analysis": True
                }
            ),
            WidgetConfiguration(
                widget_id="incident_overview_map",
                widget_type=DashboardWidget.FIRE_MAP,
                title="Incident Overview",
                position={"x": 0, "y": 2, "width": 8, "height": 5},
                data_source="incident_summary",
                refresh_interval=900,
                filters=["reporting_period", "organizational_unit"],
                custom_settings={
                    "summary_view": True,
                    "impact_visualization": True,
                    "resource_allocation": True
                }
            ),
            WidgetConfiguration(
                widget_id="resource_utilization",
                widget_type=DashboardWidget.DATA_METRICS,
                title="Resource Utilization",
                position={"x": 8, "y": 2, "width": 4, "height": 3},
                data_source="resource_tracking",
                refresh_interval=1200,
                filters=["reporting_period", "organizational_unit"],
                custom_settings={
                    "resource_types": ["personnel", "equipment", "aircraft", "budget"],
                    "efficiency_metrics": True,
                    "cost_analysis": True
                }
            ),
            WidgetConfiguration(
                widget_id="performance_indicators",
                widget_type=DashboardWidget.ANALYSIS_RESULTS,
                title="Performance Indicators",
                position={"x": 8, "y": 5, "width": 4, "height": 2},
                data_source="performance_metrics",
                refresh_interval=1800,
                filters=["reporting_period", "organizational_unit"],
                custom_settings={
                    "target_vs_actual": True,
                    "benchmark_comparison": True,
                    "goal_tracking": True
                }
            ),
            WidgetConfiguration(
                widget_id="compliance_status",
                widget_type=DashboardWidget.COMPLIANCE_REPORT,
                title="Compliance and Reporting Status",
                position={"x": 0, "y": 7, "width": 6, "height": 3},
                data_source="compliance_tracking",
                refresh_interval=3600,
                filters=["reporting_period"],
                custom_settings={
                    "regulatory_requirements": True,
                    "audit_readiness": True,
                    "documentation_status": True
                }
            ),
            WidgetConfiguration(
                widget_id="forecast_outlook",
                widget_type=DashboardWidget.FORECAST_PANEL,
                title="Forecast and Planning Outlook",
                position={"x": 6, "y": 7, "width": 6, "height": 3},
                data_source="planning_forecasts",
                refresh_interval=3600,
                filters=["organizational_unit"],
                custom_settings={
                    "seasonal_outlook": True,
                    "resource_planning": True,
                    "budget_projections": True
                }
            )
        ]

        return DashboardLayout(
            dashboard_id="business_executive",
            name="Executive Business Dashboard",
            description="High-level performance metrics and strategic overview",
            user_role="business_user",
            widgets=widgets,
            filters=filters,
            default_view={
                "zoom_level": 5,
                "center_lat": 37.5,
                "center_lon": -119.5,
                "time_window": "current_month"
            },
            is_customizable=False  # More restricted customization for executives
        )

class DashboardManager:
    """Manages dashboard creation and customization for different user roles"""

    def __init__(self):
        self.dashboard_types = {
            "data_scientist": DataScientistDashboard,
            "analyst": AnalystDashboard,
            "business_user": BusinessUserDashboard
        }
        self.user_dashboards: Dict[str, BaseDashboard] = {}

    def create_dashboard(self, user_id: str, user_role: str) -> BaseDashboard:
        """Create a dashboard for a specific user"""
        if user_role not in self.dashboard_types:
            raise ValueError(f"Unsupported user role: {user_role}")

        dashboard_class = self.dashboard_types[user_role]
        dashboard = dashboard_class(user_id, user_role)
        self.user_dashboards[user_id] = dashboard

        return dashboard

    def get_dashboard(self, user_id: str) -> Optional[BaseDashboard]:
        """Get existing dashboard for a user"""
        return self.user_dashboards.get(user_id)

    def customize_dashboard(self, user_id: str, customizations: Dict[str, Any]) -> bool:
        """Apply customizations to a user's dashboard"""
        dashboard = self.user_dashboards.get(user_id)
        if not dashboard:
            return False

        if not dashboard.layout.is_customizable:
            return False

        # Apply widget customizations
        for widget_id, settings in customizations.get("widgets", {}).items():
            dashboard.customize_widget(widget_id, settings)

        # Apply filter customizations
        for filter_id, value in customizations.get("filters", {}).items():
            dashboard.apply_filter(filter_id, value)

        return True

    def get_dashboard_config(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard configuration for frontend rendering"""
        dashboard = self.user_dashboards.get(user_id)
        if not dashboard:
            return {}

        return {
            "layout": asdict(dashboard.layout),
            "active_filters": dashboard.active_filters,
            "custom_settings": dashboard.custom_settings,
            "user_permissions": self._get_user_permissions(dashboard.user_role)
        }

    def _get_user_permissions(self, user_role: str) -> Dict[str, bool]:
        """Get user permissions based on role"""
        base_permissions = {
            "view_public_data": True,
            "export_data": False,
            "customize_dashboard": True,
            "share_dashboard": False,
            "admin_functions": False
        }

        role_permissions = {
            "data_scientist": {
                "view_public_data": True,
                "view_internal_data": True,
                "export_data": True,
                "customize_dashboard": True,
                "share_dashboard": True,
                "advanced_analytics": True
            },
            "analyst": {
                "view_public_data": True,
                "view_internal_data": True,
                "view_restricted_data": True,
                "export_data": True,
                "customize_dashboard": True,
                "real_time_alerts": True
            },
            "business_user": {
                "view_public_data": True,
                "view_summary_data": True,
                "export_reports": True,
                "customize_dashboard": False,
                "executive_functions": True
            }
        }

        return {**base_permissions, **role_permissions.get(user_role, {})}

    def get_all_dashboard_types(self) -> List[Dict[str, Any]]:
        """Get information about all available dashboard types"""
        return [
            {
                "role": "data_scientist",
                "name": "Data Scientist Research Dashboard",
                "description": "Advanced analytics and research tools",
                "features": ["Statistical analysis", "ML models", "Data quality metrics", "Correlation analysis"]
            },
            {
                "role": "analyst",
                "name": "Fire Analyst Operational Dashboard",
                "description": "Real-time monitoring and incident response",
                "features": ["Live fire detection", "Alert management", "Sensor monitoring", "Weather tracking"]
            },
            {
                "role": "business_user",
                "name": "Executive Business Dashboard",
                "description": "Strategic overview and performance metrics",
                "features": ["Executive summary", "Performance indicators", "Compliance tracking", "Resource utilization"]
            }
        ]

# Global dashboard manager instance
dashboard_manager = DashboardManager()

def get_dashboard_manager() -> DashboardManager:
    """Get the global dashboard manager instance"""
    return dashboard_manager