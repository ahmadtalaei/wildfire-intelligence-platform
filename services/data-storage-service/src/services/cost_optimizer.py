"""
Cost Optimization Service - Challenge 2 Enhancement
Intelligent cost management and optimization for hybrid storage
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

import aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

class CostCategory(Enum):
    """Cost categories for tracking"""
    STORAGE = "storage"
    COMPUTE = "compute"
    NETWORK = "network"
    MANAGEMENT = "management"

class OptimizationStrategy(Enum):
    """Cost optimization strategies"""
    LIFECYCLE_TIERING = "lifecycle_tiering"
    DEDUPLICATION = "deduplication"
    COMPRESSION = "compression"
    INTELLIGENT_CACHING = "intelligent_caching"
    USAGE_PREDICTION = "usage_prediction"

@dataclass
class CostMetric:
    """Cost measurement and tracking"""
    period_start: datetime
    period_end: datetime
    category: str
    provider: str
    service: str
    usage_amount: float
    usage_unit: str
    cost_usd: float
    budget_allocated: float
    budget_remaining: float
    cost_per_unit: float
    optimization_potential: float

@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation"""
    strategy: str
    description: str
    potential_savings_usd: float
    potential_savings_percent: float
    implementation_effort: str  # low, medium, high
    risk_level: str  # low, medium, high
    timeline_days: int
    prerequisites: List[str]
    implementation_steps: List[str]

@dataclass
class BudgetAlert:
    """Budget monitoring alert"""
    alert_id: str
    category: str
    current_spend: float
    budget_limit: float
    utilization_percent: float
    alert_level: str  # warning, critical
    projected_overage: float
    days_remaining: int

class CostOptimizer:
    """
    Intelligent cost optimization service for hybrid storage architecture

    Features:
    - Real-time cost tracking across all storage tiers
    - Predictive budget management and alerting
    - Automated optimization recommendations
    - ROI analysis for storage investments
    - Multi-cloud cost comparison and optimization
    """

    def __init__(self, db_manager, hybrid_storage_manager):
        self.db_manager = db_manager
        self.hybrid_storage = hybrid_storage_manager
        self.redis_client = None

        # Cost tracking
        self.cost_metrics = {}
        self.optimization_history = []

        # Budget configurations
        self.budget_limits = self._initialize_budget_limits()

        # Optimization thresholds
        self.optimization_thresholds = {
            "tier_usage_efficiency": 0.70,  # Trigger if tier usage < 70%
            "duplicate_ratio": 0.05,        # Alert if duplicates > 5%
            "compression_ratio": 0.30,      # Recommend if compression < 30%
            "cache_hit_ratio": 0.80,        # Optimize if cache hit < 80%
            "cost_variance_percent": 0.15   # Alert if cost variance > 15%
        }

    async def initialize(self):
        """Initialize cost optimizer"""
        logger.info("Initializing Cost Optimizer")

        # Connect to Redis for cost metrics caching
        self.redis_client = aioredis.from_url(
            "redis://localhost:6379/2",
            encoding="utf-8",
            decode_responses=True
        )

        # Create cost tracking tables
        await self._create_cost_tables()

        # Start background optimization tasks
        asyncio.create_task(self._collect_cost_metrics())
        asyncio.create_task(self._monitor_budgets())
        asyncio.create_task(self._generate_optimization_recommendations())

        logger.info("Cost Optimizer initialized successfully")

    def _initialize_budget_limits(self) -> Dict[str, Dict[str, float]]:
        """Initialize budget limits by category and time period"""
        return {
            "monthly": {
                "storage": 50000.0,      # $50k/month for storage
                "compute": 30000.0,      # $30k/month for compute
                "network": 10000.0,      # $10k/month for network
                "management": 15000.0    # $15k/month for management
            },
            "annual": {
                "storage": 550000.0,     # $550k/year (10% growth)
                "compute": 330000.0,     # $330k/year
                "network": 110000.0,     # $110k/year
                "management": 165000.0   # $165k/year
            }
        }

    async def track_cost(self, metric: CostMetric):
        """Track a cost metric"""

        # Store in database for historical analysis
        await self._store_cost_metric(metric)

        # Update Redis for real-time tracking
        cost_key = f"cost:{metric.category}:{metric.provider}:{datetime.utcnow().strftime('%Y%m%d%H')}"
        cost_data = {
            "cost_usd": metric.cost_usd,
            "usage_amount": metric.usage_amount,
            "usage_unit": metric.usage_unit,
            "timestamp": metric.period_end.isoformat()
        }

        await self.redis_client.setex(
            cost_key,
            86400,  # 24 hour expiry
            json.dumps(cost_data, default=str)
        )

        # Check for budget alerts
        await self._check_budget_thresholds(metric)

        logger.info("Cost metric tracked",
                   category=metric.category,
                   provider=metric.provider,
                   cost=metric.cost_usd)

    async def get_cost_analysis(self, period_days: int = 30) -> Dict[str, Any]:
        """Get comprehensive cost analysis"""

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)

        # Get cost metrics for period
        cost_data = await self._get_cost_metrics(start_date, end_date)

        # Calculate cost breakdown
        cost_breakdown = self._calculate_cost_breakdown(cost_data)

        # Calculate trends
        cost_trends = await self._calculate_cost_trends(cost_data, period_days)

        # Get optimization opportunities
        optimization_ops = await self._identify_optimization_opportunities(cost_data)

        # Calculate ROI metrics
        roi_metrics = await self._calculate_roi_metrics(cost_data)

        # Generate budget forecasts
        budget_forecast = await self._generate_budget_forecast(cost_trends)

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": period_days
            },
            "cost_breakdown": cost_breakdown,
            "trends": cost_trends,
            "optimization_opportunities": optimization_ops,
            "roi_metrics": roi_metrics,
            "budget_forecast": budget_forecast,
            "total_cost": sum(m.cost_usd for m in cost_data),
            "cost_per_gb": self._calculate_cost_per_gb(cost_data),
            "efficiency_score": self._calculate_efficiency_score(cost_data)
        }

    async def generate_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate intelligent optimization recommendations"""

        recommendations = []

        # Analyze storage tiering efficiency
        tiering_rec = await self._analyze_tiering_efficiency()
        if tiering_rec:
            recommendations.append(tiering_rec)

        # Analyze data deduplication opportunities
        dedup_rec = await self._analyze_deduplication_opportunities()
        if dedup_rec:
            recommendations.append(dedup_rec)

        # Analyze compression opportunities
        compression_rec = await self._analyze_compression_opportunities()
        if compression_rec:
            recommendations.append(compression_rec)

        # Analyze caching optimization
        caching_rec = await self._analyze_caching_optimization()
        if caching_rec:
            recommendations.append(caching_rec)

        # Analyze provider cost comparison
        provider_rec = await self._analyze_provider_optimization()
        if provider_rec:
            recommendations.append(provider_rec)

        # Sort by potential savings
        recommendations.sort(key=lambda x: x.potential_savings_usd, reverse=True)

        return recommendations

    async def _analyze_tiering_efficiency(self) -> Optional[OptimizationRecommendation]:
        """Analyze storage tiering efficiency"""

        # Get tier usage statistics
        tier_stats = await self.hybrid_storage.get_storage_analytics()

        # Calculate tier efficiency
        total_size = tier_stats.total_size_bytes
        hot_ratio = tier_stats.hot_tier_bytes / total_size if total_size > 0 else 0
        archive_ratio = tier_stats.archive_tier_bytes / total_size if total_size > 0 else 0

        # Check if too much data in expensive tiers
        if hot_ratio > 0.20:  # More than 20% in hot tier
            potential_savings = (hot_ratio - 0.15) * total_size * 0.000000025  # $0.025/GB difference

            return OptimizationRecommendation(
                strategy=OptimizationStrategy.LIFECYCLE_TIERING.value,
                description=f"Move {(hot_ratio - 0.15)*100:.1f}% of hot tier data to warm tier based on access patterns",
                potential_savings_usd=potential_savings * 12,  # Annual savings
                potential_savings_percent=potential_savings / tier_stats.cost_per_month_usd * 100,
                implementation_effort="low",
                risk_level="low",
                timeline_days=7,
                prerequisites=["Access pattern analysis", "Data classification review"],
                implementation_steps=[
                    "Analyze data access patterns for last 30 days",
                    "Identify data not accessed in last 7 days",
                    "Configure automated tiering policies",
                    "Monitor performance impact for 24 hours"
                ]
            )

        return None

    async def _analyze_deduplication_opportunities(self) -> Optional[OptimizationRecommendation]:
        """Analyze data deduplication opportunities"""

        # Get storage statistics with deduplication analysis
        dedup_stats = await self._calculate_deduplication_stats()

        if dedup_stats["duplicate_ratio"] > self.optimization_thresholds["duplicate_ratio"]:
            storage_saved = dedup_stats["duplicate_size_gb"]
            monthly_savings = storage_saved * 0.025  # Average $0.025/GB/month

            return OptimizationRecommendation(
                strategy=OptimizationStrategy.DEDUPLICATION.value,
                description=f"Implement deduplication to eliminate {storage_saved:.1f}GB of duplicate data",
                potential_savings_usd=monthly_savings * 12,
                potential_savings_percent=monthly_savings / dedup_stats["current_monthly_cost"] * 100,
                implementation_effort="medium",
                risk_level="low",
                timeline_days=14,
                prerequisites=["Backup verification", "Performance testing"],
                implementation_steps=[
                    "Enable content-based deduplication",
                    "Run deduplication analysis",
                    "Verify data integrity",
                    "Monitor storage reduction"
                ]
            )

        return None

    async def _analyze_compression_opportunities(self) -> Optional[OptimizationRecommendation]:
        """Analyze data compression opportunities"""

        # Get compression statistics by data type
        compression_stats = await self._calculate_compression_stats()

        total_savings = 0
        recommendations = []

        for data_type, stats in compression_stats.items():
            if stats["compression_ratio"] < self.optimization_thresholds["compression_ratio"]:
                potential_compression = 0.60 - stats["compression_ratio"]  # Target 60% compression
                size_savings = stats["size_gb"] * potential_compression
                cost_savings = size_savings * 0.025 * 12  # Annual savings
                total_savings += cost_savings

        if total_savings > 1000:  # If savings > $1000/year
            return OptimizationRecommendation(
                strategy=OptimizationStrategy.COMPRESSION.value,
                description=f"Implement advanced compression algorithms for better storage efficiency",
                potential_savings_usd=total_savings,
                potential_savings_percent=total_savings / (compression_stats["total_monthly_cost"] * 12) * 100,
                implementation_effort="medium",
                risk_level="low",
                timeline_days=21,
                prerequisites=["Compression algorithm testing", "Performance impact analysis"],
                implementation_steps=[
                    "Test compression algorithms on sample data",
                    "Measure compression ratios and CPU impact",
                    "Deploy compression policies by data type",
                    "Monitor storage reduction and performance"
                ]
            )

        return None

    async def _analyze_caching_optimization(self) -> Optional[OptimizationRecommendation]:
        """Analyze caching optimization opportunities"""

        # Get cache performance statistics
        cache_stats = await self._get_cache_statistics()

        if cache_stats["hit_ratio"] < self.optimization_thresholds["cache_hit_ratio"]:
            # Calculate potential savings from improved cache hit ratio
            current_cloud_requests = cache_stats["total_requests"] * (1 - cache_stats["hit_ratio"])
            improved_hit_ratio = 0.85  # Target 85% cache hit ratio
            optimized_cloud_requests = cache_stats["total_requests"] * (1 - improved_hit_ratio)

            request_savings = current_cloud_requests - optimized_cloud_requests
            monthly_savings = request_savings * 0.0004  # $0.0004 per request average

            return OptimizationRecommendation(
                strategy=OptimizationStrategy.INTELLIGENT_CACHING.value,
                description=f"Optimize caching strategy to improve hit ratio from {cache_stats['hit_ratio']*100:.1f}% to 85%",
                potential_savings_usd=monthly_savings * 12,
                potential_savings_percent=monthly_savings / cache_stats["monthly_cloud_cost"] * 100,
                implementation_effort="medium",
                risk_level="low",
                timeline_days=10,
                prerequisites=["Cache usage analysis", "Memory capacity planning"],
                implementation_steps=[
                    "Analyze cache access patterns",
                    "Implement intelligent cache warming",
                    "Optimize cache eviction policies",
                    "Monitor cache performance improvements"
                ]
            )

        return None

    async def _monitor_budgets(self):
        """Background task to monitor budget compliance"""

        while True:
            try:
                # Get current month spending
                current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                current_spending = await self._get_current_spending(current_month_start)

                # Check monthly budget limits
                for category, spending in current_spending.items():
                    budget_limit = self.budget_limits["monthly"].get(category, 0)
                    utilization = spending / budget_limit if budget_limit > 0 else 0

                    if utilization > 0.80:  # 80% threshold
                        alert = BudgetAlert(
                            alert_id=f"budget_{category}_{datetime.utcnow().strftime('%Y%m%d')}",
                            category=category,
                            current_spend=spending,
                            budget_limit=budget_limit,
                            utilization_percent=utilization * 100,
                            alert_level="warning" if utilization < 0.95 else "critical",
                            projected_overage=max(0, spending - budget_limit),
                            days_remaining=(datetime.utcnow().replace(month=datetime.utcnow().month+1, day=1) - datetime.utcnow()).days
                        )

                        await self._send_budget_alert(alert)

            except Exception as e:
                logger.error("Error monitoring budgets", error=str(e))

            await asyncio.sleep(3600)  # Check every hour

    async def _create_cost_tables(self):
        """Create database tables for cost tracking"""

        create_cost_metrics_table = """
        CREATE TABLE IF NOT EXISTS cost_metrics (
            metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            period_start TIMESTAMP NOT NULL,
            period_end TIMESTAMP NOT NULL,
            category VARCHAR(50) NOT NULL,
            provider VARCHAR(50) NOT NULL,
            service VARCHAR(100) NOT NULL,
            usage_amount DECIMAL(15,6) NOT NULL,
            usage_unit VARCHAR(20) NOT NULL,
            cost_usd DECIMAL(10,2) NOT NULL,
            budget_allocated DECIMAL(10,2),
            cost_per_unit DECIMAL(10,6),
            optimization_potential DECIMAL(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_cost_metrics_period ON cost_metrics(period_start, period_end);
        CREATE INDEX IF NOT EXISTS idx_cost_metrics_category ON cost_metrics(category);
        CREATE INDEX IF NOT EXISTS idx_cost_metrics_provider ON cost_metrics(provider);
        """

        create_optimization_history_table = """
        CREATE TABLE IF NOT EXISTS optimization_history (
            optimization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            strategy VARCHAR(50) NOT NULL,
            implementation_date TIMESTAMP NOT NULL,
            projected_savings DECIMAL(10,2) NOT NULL,
            actual_savings DECIMAL(10,2),
            savings_period_months INTEGER,
            success_status VARCHAR(20) DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_optimization_history_date ON optimization_history(implementation_date);
        CREATE INDEX IF NOT EXISTS idx_optimization_history_strategy ON optimization_history(strategy);
        """

        async with self.db_manager.get_session() as session:
            await session.execute(create_cost_metrics_table)
            await session.execute(create_optimization_history_table)
            await session.commit()

    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()

    # Additional helper methods for cost calculations, trend analysis, etc.
    def _calculate_cost_breakdown(self, cost_data: List[CostMetric]) -> Dict[str, Any]:
        """Calculate cost breakdown by category, provider, service"""
        breakdown = {
            "by_category": {},
            "by_provider": {},
            "by_service": {}
        }

        for metric in cost_data:
            # By category
            if metric.category not in breakdown["by_category"]:
                breakdown["by_category"][metric.category] = {"cost": 0, "usage": 0}
            breakdown["by_category"][metric.category]["cost"] += metric.cost_usd
            breakdown["by_category"][metric.category]["usage"] += metric.usage_amount

            # By provider
            if metric.provider not in breakdown["by_provider"]:
                breakdown["by_provider"][metric.provider] = {"cost": 0, "usage": 0}
            breakdown["by_provider"][metric.provider]["cost"] += metric.cost_usd
            breakdown["by_provider"][metric.provider]["usage"] += metric.usage_amount

            # By service
            if metric.service not in breakdown["by_service"]:
                breakdown["by_service"][metric.service] = {"cost": 0, "usage": 0}
            breakdown["by_service"][metric.service]["cost"] += metric.cost_usd
            breakdown["by_service"][metric.service]["usage"] += metric.usage_amount

        return breakdown