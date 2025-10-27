"""
Latency & Fidelity Metrics Dashboard - Challenge 1 Enhancement
Real-time monitoring of data ingestion performance and quality metrics
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import aioredis
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import structlog
from prometheus_client import Histogram, Counter, Gauge, generate_latest

logger = structlog.get_logger()

class IngestionMode(Enum):
    """Data ingestion modes for monitoring"""
    BATCH = "batch"
    REAL_TIME = "real_time"
    STREAMING = "streaming"

class DataFormat(Enum):
    """Supported data formats"""
    JSON = "json"
    CSV = "csv"
    NETCDF = "netcdf"
    GEOTIFF = "geotiff"
    XML = "xml"
    BINARY = "binary"

@dataclass
class LatencyMetric:
    """Latency measurement for data ingestion"""
    source: str
    ingestion_mode: str
    data_format: str
    ingestion_start: datetime
    processing_start: datetime
    processing_end: datetime
    storage_complete: datetime
    total_latency_ms: float
    processing_latency_ms: float
    storage_latency_ms: float
    network_latency_ms: float

@dataclass
class FidelityMetric:
    """Data fidelity and quality measurement"""
    source: str
    data_format: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_fields: int
    schema_errors: int
    fidelity_score: float  # 0.0 to 1.0
    quality_issues: List[str]
    validation_time_ms: float

@dataclass
class ThroughputMetric:
    """Data throughput measurement"""
    source: str
    ingestion_mode: str
    bytes_per_second: float
    records_per_second: float
    concurrent_streams: int
    timestamp: datetime

class LatencyFidelityDashboard:
    """
    Real-time dashboard for monitoring data ingestion latency and fidelity

    Features:
    - Real-time latency tracking across ingestion modes
    - Data quality and fidelity validation
    - Performance bottleneck identification
    - SLA monitoring and alerting
    - Historical trend analysis
    """

    def __init__(self):
        self.redis_client = None
        self.active_connections = set()

        # Prometheus metrics
        self.latency_histogram = Histogram(
            'data_ingestion_latency_seconds',
            'Data ingestion latency by mode and format',
            ['source', 'mode', 'format', 'stage']
        )

        self.fidelity_gauge = Gauge(
            'data_fidelity_score',
            'Data fidelity score by source and format',
            ['source', 'format']
        )

        self.throughput_gauge = Gauge(
            'data_throughput_bytes_per_second',
            'Data throughput in bytes per second',
            ['source', 'mode']
        )

        self.error_counter = Counter(
            'data_ingestion_errors_total',
            'Total data ingestion errors',
            ['source', 'error_type']
        )

    async def initialize(self):
        """Initialize the dashboard services"""
        logger.info("Initializing Latency & Fidelity Dashboard")

        # Connect to Redis for metrics storage
        self.redis_client = aioredis.from_url(
            "redis://localhost:6379/1",
            encoding="utf-8",
            decode_responses=True
        )

        # Start background monitoring tasks
        asyncio.create_task(self._collect_metrics_from_services())
        asyncio.create_task(self._analyze_performance_trends())
        asyncio.create_task(self._check_sla_violations())

        logger.info("Dashboard initialized successfully")

    async def record_latency_metric(self, metric: LatencyMetric):
        """Record a latency measurement"""

        # Update Prometheus metrics
        self.latency_histogram.labels(
            source=metric.source,
            mode=metric.ingestion_mode,
            format=metric.data_format,
            stage="total"
        ).observe(metric.total_latency_ms / 1000)

        self.latency_histogram.labels(
            source=metric.source,
            mode=metric.ingestion_mode,
            format=metric.data_format,
            stage="processing"
        ).observe(metric.processing_latency_ms / 1000)

        # Store in Redis for real-time dashboard
        metric_key = f"latency:{metric.source}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.redis_client.setex(
            metric_key,
            3600,  # 1 hour expiry
            json.dumps(asdict(metric), default=str)
        )

        # Broadcast to WebSocket connections
        await self._broadcast_latency_update(metric)

        logger.info("Latency metric recorded",
                   source=metric.source,
                   mode=metric.ingestion_mode,
                   total_latency=metric.total_latency_ms)

    async def record_fidelity_metric(self, metric: FidelityMetric):
        """Record a fidelity measurement"""

        # Update Prometheus metrics
        self.fidelity_gauge.labels(
            source=metric.source,
            format=metric.data_format
        ).set(metric.fidelity_score)

        # Count errors by type
        for issue in metric.quality_issues:
            self.error_counter.labels(
                source=metric.source,
                error_type=issue
            ).inc()

        # Store in Redis
        metric_key = f"fidelity:{metric.source}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.redis_client.setex(
            metric_key,
            3600,
            json.dumps(asdict(metric), default=str)
        )

        # Broadcast to WebSocket connections
        await self._broadcast_fidelity_update(metric)

        logger.info("Fidelity metric recorded",
                   source=metric.source,
                   fidelity_score=metric.fidelity_score,
                   quality_issues=len(metric.quality_issues))

    async def record_throughput_metric(self, metric: ThroughputMetric):
        """Record a throughput measurement"""

        # Update Prometheus metrics
        self.throughput_gauge.labels(
            source=metric.source,
            mode=metric.ingestion_mode
        ).set(metric.bytes_per_second)

        # Store in Redis
        metric_key = f"throughput:{metric.source}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.redis_client.setex(
            metric_key,
            300,  # 5 minute expiry for high-frequency data
            json.dumps(asdict(metric), default=str)
        )

        # Broadcast to WebSocket connections
        await self._broadcast_throughput_update(metric)

    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics summary"""

        current_time = datetime.utcnow()
        five_minutes_ago = current_time - timedelta(minutes=5)

        # Get recent latency metrics
        latency_metrics = await self._get_recent_metrics("latency", five_minutes_ago)

        # Get recent fidelity metrics
        fidelity_metrics = await self._get_recent_metrics("fidelity", five_minutes_ago)

        # Get recent throughput metrics
        throughput_metrics = await self._get_recent_metrics("throughput", five_minutes_ago)

        # Calculate aggregated statistics
        latency_stats = self._calculate_latency_stats(latency_metrics)
        fidelity_stats = self._calculate_fidelity_stats(fidelity_metrics)
        throughput_stats = self._calculate_throughput_stats(throughput_metrics)

        return {
            "timestamp": current_time.isoformat(),
            "latency": latency_stats,
            "fidelity": fidelity_stats,
            "throughput": throughput_stats,
            "sla_status": await self._get_sla_status(),
            "alerts": await self._get_active_alerts()
        }

    async def get_historical_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Get historical performance analysis"""

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Get historical data
        latency_history = await self._get_historical_metrics("latency", start_time, end_time)
        fidelity_history = await self._get_historical_metrics("fidelity", start_time, end_time)

        # Analyze trends
        latency_trends = self._analyze_latency_trends(latency_history)
        fidelity_trends = self._analyze_fidelity_trends(fidelity_history)

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "latency_trends": latency_trends,
            "fidelity_trends": fidelity_trends,
            "performance_summary": self._generate_performance_summary(latency_history, fidelity_history),
            "recommendations": self._generate_optimization_recommendations(latency_trends, fidelity_trends)
        }

    async def _collect_metrics_from_services(self):
        """Background task to collect metrics from other services"""

        while True:
            try:
                # Collect from data ingestion service
                await self._collect_from_ingestion_service()

                # Collect from data storage service
                await self._collect_from_storage_service()

                # Collect from fire risk service
                await self._collect_from_fire_risk_service()

            except Exception as e:
                logger.error("Error collecting metrics from services", error=str(e))

            await asyncio.sleep(10)  # Collect every 10 seconds

    async def _collect_from_ingestion_service(self):
        """Collect metrics from data ingestion service"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://data-ingestion-service:8003/metrics/latency") as response:
                    if response.status == 200:
                        data = await response.json()

                        for metric_data in data.get("latency_metrics", []):
                            metric = LatencyMetric(**metric_data)
                            await self.record_latency_metric(metric)

                async with session.get("http://data-ingestion-service:8003/metrics/fidelity") as response:
                    if response.status == 200:
                        data = await response.json()

                        for metric_data in data.get("fidelity_metrics", []):
                            metric = FidelityMetric(**metric_data)
                            await self.record_fidelity_metric(metric)

        except Exception as e:
            logger.warning("Failed to collect from ingestion service", error=str(e))

    async def _analyze_performance_trends(self):
        """Background task to analyze performance trends"""

        while True:
            try:
                # Analyze hourly trends
                trends = await self.get_historical_analysis(hours=1)

                # Check for performance degradation
                if trends["latency_trends"]["degradation_detected"]:
                    await self._trigger_performance_alert("latency_degradation", trends)

                if trends["fidelity_trends"]["quality_decline"]:
                    await self._trigger_performance_alert("fidelity_decline", trends)

            except Exception as e:
                logger.error("Error analyzing performance trends", error=str(e))

            await asyncio.sleep(300)  # Analyze every 5 minutes

    async def _check_sla_violations(self):
        """Background task to check SLA violations"""

        sla_thresholds = {
            "latency_p99_ms": 5000,    # 99th percentile < 5 seconds
            "latency_p95_ms": 2000,    # 95th percentile < 2 seconds
            "fidelity_score": 0.95,    # 95% data quality
            "availability": 0.999      # 99.9% uptime
        }

        while True:
            try:
                current_metrics = await self.get_real_time_metrics()

                # Check latency SLA
                if current_metrics["latency"]["p99_ms"] > sla_thresholds["latency_p99_ms"]:
                    await self._trigger_sla_alert("latency_sla_violation", current_metrics)

                # Check fidelity SLA
                if current_metrics["fidelity"]["average_score"] < sla_thresholds["fidelity_score"]:
                    await self._trigger_sla_alert("fidelity_sla_violation", current_metrics)

            except Exception as e:
                logger.error("Error checking SLA violations", error=str(e))

            await asyncio.sleep(60)  # Check every minute

    def _calculate_latency_stats(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate latency statistics"""
        if not metrics:
            return {"count": 0}

        latencies = [m["total_latency_ms"] for m in metrics]
        latencies.sort()

        count = len(latencies)
        return {
            "count": count,
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "avg_ms": sum(latencies) / count,
            "p50_ms": latencies[int(count * 0.5)],
            "p95_ms": latencies[int(count * 0.95)],
            "p99_ms": latencies[int(count * 0.99)],
            "by_mode": self._group_by_field(metrics, "ingestion_mode", "total_latency_ms"),
            "by_format": self._group_by_field(metrics, "data_format", "total_latency_ms")
        }

    def _calculate_fidelity_stats(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate fidelity statistics"""
        if not metrics:
            return {"count": 0}

        scores = [m["fidelity_score"] for m in metrics]

        return {
            "count": len(metrics),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "total_records": sum(m["total_records"] for m in metrics),
            "total_valid": sum(m["valid_records"] for m in metrics),
            "total_invalid": sum(m["invalid_records"] for m in metrics),
            "by_source": self._group_by_field(metrics, "source", "fidelity_score"),
            "by_format": self._group_by_field(metrics, "data_format", "fidelity_score")
        }

    async def _broadcast_latency_update(self, metric: LatencyMetric):
        """Broadcast latency update to WebSocket connections"""
        message = {
            "type": "latency_update",
            "data": asdict(metric)
        }
        await self._broadcast_to_connections(message)

    async def _broadcast_fidelity_update(self, metric: FidelityMetric):
        """Broadcast fidelity update to WebSocket connections"""
        message = {
            "type": "fidelity_update",
            "data": asdict(metric)
        }
        await self._broadcast_to_connections(message)

    async def _broadcast_to_connections(self, message: Dict):
        """Broadcast message to all WebSocket connections"""
        if self.active_connections:
            message_str = json.dumps(message, default=str)
            disconnected = set()

            for websocket in self.active_connections:
                try:
                    await websocket.send_text(message_str)
                except:
                    disconnected.add(websocket)

            # Remove disconnected connections
            self.active_connections -= disconnected

    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()

# Dashboard HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>CAL FIRE - Latency & Fidelity Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #d32f2f; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333; }
        .metric-value { font-size: 24px; font-weight: bold; color: #1976d2; }
        .metric-unit { font-size: 14px; color: #666; }
        .status-good { color: #4caf50; }
        .status-warning { color: #ff9800; }
        .status-error { color: #f44336; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .real-time-indicator { display: inline-block; width: 12px; height: 12px; background: #4caf50; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="header">
        <h1><span class="real-time-indicator"></span>CAL FIRE Wildfire Intelligence Platform</h1>
        <h2>Challenge 1: Data Ingestion Latency & Fidelity Dashboard</h2>
        <p>Real-time monitoring of data ingestion performance across all sources and formats</p>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">Average Latency</div>
            <div class="metric-value" id="avg-latency">--</div>
            <div class="metric-unit">milliseconds</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Data Fidelity Score</div>
            <div class="metric-value" id="fidelity-score">--</div>
            <div class="metric-unit">% quality</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Throughput</div>
            <div class="metric-value" id="throughput">--</div>
            <div class="metric-unit">records/second</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">SLA Status</div>
            <div class="metric-value" id="sla-status">--</div>
            <div class="metric-unit">compliance</div>
        </div>
    </div>

    <div class="chart-container">
        <h3>Real-Time Latency by Ingestion Mode</h3>
        <canvas id="latencyChart" width="800" height="300"></canvas>
    </div>

    <div class="chart-container">
        <h3>Data Fidelity by Source</h3>
        <canvas id="fidelityChart" width="800" height="300"></canvas>
    </div>

    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket('ws://localhost:8004/ws');

        // Initialize charts
        const latencyCtx = document.getElementById('latencyChart').getContext('2d');
        const fidelityCtx = document.getElementById('fidelityChart').getContext('2d');

        const latencyChart = new Chart(latencyCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Batch',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }, {
                    label: 'Real-time',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1
                }, {
                    label: 'Streaming',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Latency (ms)'
                        }
                    }
                }
            }
        });

        const fidelityChart = new Chart(fidelityCtx, {
            type: 'bar',
            data: {
                labels: ['NASA FIRMS', 'NOAA Weather', 'CAL FIRE', 'IoT Sensors', 'Satellite'],
                datasets: [{
                    label: 'Fidelity Score',
                    data: [],
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Fidelity Score (%)'
                        }
                    }
                }
            }
        });

        // WebSocket message handlers
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);

            if (message.type === 'metrics_update') {
                updateDashboard(message.data);
            }
        };

        function updateDashboard(data) {
            // Update metric cards
            document.getElementById('avg-latency').textContent = Math.round(data.latency.avg_ms || 0);
            document.getElementById('fidelity-score').textContent = Math.round((data.fidelity.average_score || 0) * 100);
            document.getElementById('throughput').textContent = Math.round(data.throughput.avg_records_per_second || 0);

            const slaElement = document.getElementById('sla-status');
            slaElement.textContent = data.sla_status?.status || 'Unknown';
            slaElement.className = 'metric-value ' + (data.sla_status?.status === 'Compliant' ? 'status-good' : 'status-error');

            // Update charts with new data
            updateLatencyChart(data.latency);
            updateFidelityChart(data.fidelity);
        }

        function updateLatencyChart(latencyData) {
            const now = new Date().toLocaleTimeString();

            if (latencyChart.data.labels.length > 20) {
                latencyChart.data.labels.shift();
                latencyChart.data.datasets.forEach(dataset => dataset.data.shift());
            }

            latencyChart.data.labels.push(now);
            latencyChart.data.datasets[0].data.push(latencyData.by_mode?.batch?.avg || 0);
            latencyChart.data.datasets[1].data.push(latencyData.by_mode?.real_time?.avg || 0);
            latencyChart.data.datasets[2].data.push(latencyData.by_mode?.streaming?.avg || 0);

            latencyChart.update('none');
        }

        function updateFidelityChart(fidelityData) {
            if (fidelityData.by_source) {
                fidelityChart.data.datasets[0].data = [
                    (fidelityData.by_source['nasa_firms']?.avg || 0) * 100,
                    (fidelityData.by_source['noaa_weather']?.avg || 0) * 100,
                    (fidelityData.by_source['calfire']?.avg || 0) * 100,
                    (fidelityData.by_source['iot_sensors']?.avg || 0) * 100,
                    (fidelityData.by_source['satellite']?.avg || 0) * 100
                ];
                fidelityChart.update('none');
            }
        }

        // Fetch initial data
        fetch('/api/metrics/current')
            .then(response => response.json())
            .then(data => updateDashboard(data))
            .catch(error => console.error('Error fetching initial data:', error));

        // Refresh data every 5 seconds
        setInterval(() => {
            fetch('/api/metrics/current')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error fetching data:', error));
        }, 5000);
    </script>
</body>
</html>
"""