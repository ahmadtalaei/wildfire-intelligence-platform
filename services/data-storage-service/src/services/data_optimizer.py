"""
Data Storage Service - Data Optimizer
Automated data optimization service for performance tuning and storage efficiency
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from collections import defaultdict
import structlog

from ..config import get_settings
from ..models.data_models import DataType
from ..models.database import DatabaseManager
from ..models.timeseries import TimeseriesManager

logger = structlog.get_logger()

class OptimizationType(str, Enum):
    INDEX_MAINTENANCE = "index_maintenance"
    COMPRESSION = "compression"
    PARTITIONING = "partitioning"
    VACUUM = "vacuum"
    ANALYZE = "analyze"
    CONTINUOUS_AGGREGATES = "continuous_aggregates"
    CHUNK_OPTIMIZATION = "chunk_optimization"
    QUERY_PLAN_CACHE = "query_plan_cache"

class OptimizationPriority(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class OptimizationResult:
    """Result of an optimization operation"""
    
    def __init__(self, optimization_type: OptimizationType, success: bool, 
                 message: str, details: Dict[str, Any] = None,
                 execution_time_seconds: float = 0, 
                 performance_impact: str = "unknown"):
        self.optimization_type = optimization_type
        self.success = success
        self.message = message
        self.details = details or {}
        self.execution_time_seconds = execution_time_seconds
        self.performance_impact = performance_impact
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimization_type": self.optimization_type.value,
            "success": self.success,
            "message": self.message,
            "details": self.details,
            "execution_time_seconds": self.execution_time_seconds,
            "performance_impact": self.performance_impact,
            "timestamp": self.timestamp.isoformat()
        }

class DataOptimizer:
    """
    Comprehensive data optimization service for automated performance tuning
    
    Features:
    - Automatic index optimization and maintenance
    - TimescaleDB chunk and compression optimization
    - Database vacuum and analyze operations
    - Continuous aggregate refresh and optimization
    - Query performance monitoring and optimization
    - Storage space optimization
    - Partition maintenance and pruning
    - Statistics collection and analysis
    """
    
    def __init__(self, db_manager: DatabaseManager, timeseries_manager: TimeseriesManager):
        self.db_manager = db_manager
        self.timeseries_manager = timeseries_manager
        self.settings = get_settings()
        
        # Optimization scheduling
        self.optimization_schedule = {
            OptimizationType.ANALYZE: timedelta(hours=6),       # Every 6 hours
            OptimizationType.VACUUM: timedelta(days=1),         # Daily
            OptimizationType.INDEX_MAINTENANCE: timedelta(days=7), # Weekly
            OptimizationType.COMPRESSION: timedelta(days=1),    # Daily
            OptimizationType.CHUNK_OPTIMIZATION: timedelta(hours=12), # Every 12 hours
            OptimizationType.CONTINUOUS_AGGREGATES: timedelta(hours=1), # Hourly
        }
        
        # Performance thresholds
        self.performance_thresholds = {
            'slow_query_threshold_ms': 5000,     # 5 seconds
            'index_scan_ratio_threshold': 0.95,  # 95% index scans
            'cache_hit_ratio_threshold': 0.90,   # 90% cache hits
            'table_bloat_threshold': 20,         # 20% bloat
            'chunk_size_threshold_mb': 100,      # 100MB per chunk
        }
        
        # Optimization history tracking
        self.optimization_history: List[OptimizationResult] = []
        self.last_optimization_times: Dict[OptimizationType, datetime] = {}
        
        # Active optimization tasks
        self.active_optimizations: Dict[str, Dict] = {}
        
    async def optimize_all(self) -> Dict[str, Any]:
        """Run comprehensive optimization of all storage components"""
        start_time = time.time()
        results = []
        
        logger.info("Starting comprehensive data optimization")
        
        # Define optimization sequence (order matters for some operations)
        optimization_sequence = [
            (self._analyze_tables, OptimizationType.ANALYZE, OptimizationPriority.HIGH),
            (self._optimize_indexes, OptimizationType.INDEX_MAINTENANCE, OptimizationPriority.MEDIUM),
            (self._vacuum_tables, OptimizationType.VACUUM, OptimizationPriority.MEDIUM),
            (self._optimize_timescale_chunks, OptimizationType.CHUNK_OPTIMIZATION, OptimizationPriority.HIGH),
            (self._optimize_compression, OptimizationType.COMPRESSION, OptimizationPriority.MEDIUM),
            (self._refresh_continuous_aggregates, OptimizationType.CONTINUOUS_AGGREGATES, OptimizationPriority.HIGH),
        ]
        
        # Execute optimizations
        for optimization_func, opt_type, priority in optimization_sequence:
            try:
                # Check if optimization is needed based on schedule
                if not self._is_optimization_needed(opt_type):
                    logger.info("Optimization skipped - not needed yet", 
                               optimization_type=opt_type.value)
                    continue
                
                logger.info("Starting optimization", optimization_type=opt_type.value)
                result = await optimization_func()
                results.append(result)
                
                # Update last optimization time
                self.last_optimization_times[opt_type] = datetime.utcnow()
                
            except Exception as e:
                error_result = OptimizationResult(
                    optimization_type=opt_type,
                    success=False,
                    message=f"Optimization failed: {str(e)}",
                    execution_time_seconds=time.time() - start_time
                )
                results.append(error_result)
                logger.error("Optimization failed", 
                           optimization_type=opt_type.value,
                           error=str(e))
        
        # Collect performance statistics
        performance_stats = await self._collect_performance_stats()
        
        total_time = time.time() - start_time
        
        summary = {
            "total_execution_time_seconds": total_time,
            "optimizations_performed": len([r for r in results if r.success]),
            "optimizations_failed": len([r for r in results if not r.success]),
            "performance_stats": performance_stats,
            "results": [r.to_dict() for r in results],
            "recommendations": await self._generate_recommendations(results, performance_stats)
        }
        
        logger.info("Comprehensive optimization completed",
                   execution_time=total_time,
                   successful_optimizations=summary["optimizations_performed"],
                   failed_optimizations=summary["optimizations_failed"])
        
        return summary
    
    async def _analyze_tables(self) -> OptimizationResult:
        """Update table statistics for query planning"""
        start_time = time.time()
        
        try:
            analyzed_tables = []
            
            # Get all tables that need statistics updates
            async with self.db_manager.get_connection() as conn:
                # Check last analyze time for all tables
                stats_query = """
                    SELECT schemaname, tablename, last_analyze, n_tup_ins, n_tup_upd, n_tup_del
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY (n_tup_ins + n_tup_upd + n_tup_del) DESC
                """
                
                tables = await conn.fetch(stats_query)
                
                for table in tables:
                    table_name = f"{table['schemaname']}.{table['tablename']}"
                    
                    # Analyze if no recent statistics or high activity
                    needs_analyze = False
                    
                    if not table['last_analyze']:
                        needs_analyze = True
                    elif table['last_analyze'] < datetime.utcnow() - timedelta(hours=12):
                        # High activity tables need more frequent analysis
                        activity = (table['n_tup_ins'] or 0) + (table['n_tup_upd'] or 0) + (table['n_tup_del'] or 0)
                        if activity > 1000:  # Threshold for high activity
                            needs_analyze = True
                    
                    if needs_analyze:
                        logger.info("Analyzing table", table=table_name)
                        await conn.execute(f"ANALYZE {table_name}")
                        analyzed_tables.append(table_name)
            
            execution_time = time.time() - start_time
            
            return OptimizationResult(
                optimization_type=OptimizationType.ANALYZE,
                success=True,
                message=f"Analyzed {len(analyzed_tables)} tables",
                details={
                    "analyzed_tables": analyzed_tables,
                    "total_tables_checked": len(tables)
                },
                execution_time_seconds=execution_time,
                performance_impact="high"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return OptimizationResult(
                optimization_type=OptimizationType.ANALYZE,
                success=False,
                message=f"Table analysis failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    async def _optimize_indexes(self) -> OptimizationResult:
        """Optimize database indexes for better query performance"""
        start_time = time.time()
        
        try:
            optimized_indexes = []
            
            async with self.db_manager.get_connection() as conn:
                # Find unused indexes
                unused_indexes_query = """
                    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE idx_scan < 10 AND schemaname = 'public'
                    ORDER BY pg_total_relation_size(indexrelid) DESC
                """
                
                unused_indexes = await conn.fetch(unused_indexes_query)
                
                # Find missing indexes (tables with low index scan ratio)
                missing_indexes_query = """
                    SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch,
                           CASE WHEN seq_scan + idx_scan = 0 THEN 0
                                ELSE idx_scan::float / (seq_scan + idx_scan)
                           END as index_ratio
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public' AND seq_scan > 1000
                    ORDER BY index_ratio ASC
                """
                
                low_index_tables = await conn.fetch(missing_indexes_query)
                
                # Reindex fragmented indexes
                fragmented_indexes_query = """
                    SELECT n.nspname, c.relname, i.relname as indexname,
                           pg_size_pretty(pg_total_relation_size(i.oid)) as size
                    FROM pg_class c
                    JOIN pg_index x ON c.oid = x.indrelid
                    JOIN pg_class i ON i.oid = x.indexrelid
                    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relkind = 'r' AND n.nspname = 'public'
                    ORDER BY pg_total_relation_size(i.oid) DESC
                    LIMIT 10
                """
                
                large_indexes = await conn.fetch(fragmented_indexes_query)
                
                # Reindex large indexes that might be fragmented
                for index in large_indexes:
                    try:
                        index_name = f"{index['nspname']}.{index['indexname']}"
                        logger.info("Reindexing", index=index_name)
                        await conn.execute(f"REINDEX INDEX {index_name}")
                        optimized_indexes.append(index_name)
                    except Exception as e:
                        logger.warning("Failed to reindex", index=index_name, error=str(e))
            
            execution_time = time.time() - start_time
            
            return OptimizationResult(
                optimization_type=OptimizationType.INDEX_MAINTENANCE,
                success=True,
                message=f"Optimized {len(optimized_indexes)} indexes",
                details={
                    "reindexed": optimized_indexes,
                    "unused_indexes": len(unused_indexes),
                    "low_index_ratio_tables": len([t for t in low_index_tables if t['index_ratio'] < 0.95])
                },
                execution_time_seconds=execution_time,
                performance_impact="high"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return OptimizationResult(
                optimization_type=OptimizationType.INDEX_MAINTENANCE,
                success=False,
                message=f"Index optimization failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    async def _vacuum_tables(self) -> OptimizationResult:
        """Perform vacuum operations to reclaim space and update statistics"""
        start_time = time.time()
        
        try:
            vacuumed_tables = []
            
            async with self.db_manager.get_connection() as conn:
                # Find tables that need vacuum based on dead tuples
                vacuum_candidates_query = """
                    SELECT schemaname, tablename, n_dead_tup, n_live_tup, last_vacuum, last_autovacuum,
                           CASE WHEN n_live_tup = 0 THEN 0
                                ELSE n_dead_tup::float / n_live_tup
                           END as dead_tuple_ratio
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                      AND (last_vacuum IS NULL OR last_vacuum < now() - interval '1 day'
                           OR n_dead_tup > 1000)
                    ORDER BY dead_tuple_ratio DESC
                """
                
                tables = await conn.fetch(vacuum_candidates_query)
                
                for table in tables:
                    table_name = f"{table['schemaname']}.{table['tablename']}"
                    dead_ratio = table['dead_tuple_ratio'] or 0
                    
                    # Determine vacuum type based on dead tuple ratio
                    if dead_ratio > 0.2:  # > 20% dead tuples
                        logger.info("Full vacuum needed", table=table_name, dead_ratio=dead_ratio)
                        await conn.execute(f"VACUUM FULL {table_name}")
                        vacuumed_tables.append(f"{table_name} (FULL)")
                    elif dead_ratio > 0.05 or table['n_dead_tup'] > 1000:  # > 5% or 1000+ dead tuples
                        logger.info("Regular vacuum", table=table_name, dead_tuples=table['n_dead_tup'])
                        await conn.execute(f"VACUUM {table_name}")
                        vacuumed_tables.append(table_name)
            
            execution_time = time.time() - start_time
            
            return OptimizationResult(
                optimization_type=OptimizationType.VACUUM,
                success=True,
                message=f"Vacuumed {len(vacuumed_tables)} tables",
                details={
                    "vacuumed_tables": vacuumed_tables,
                    "total_candidates": len(tables)
                },
                execution_time_seconds=execution_time,
                performance_impact="medium"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return OptimizationResult(
                optimization_type=OptimizationType.VACUUM,
                success=False,
                message=f"Vacuum operation failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    async def _optimize_timescale_chunks(self) -> OptimizationResult:
        """Optimize TimescaleDB chunks for better performance"""
        start_time = time.time()
        
        try:
            optimized_chunks = []
            
            async with self.timeseries_manager.get_connection() as conn:
                # Get chunk information
                chunk_info_query = """
                    SELECT 
                        hypertable_name,
                        chunk_name,
                        range_start,
                        range_end,
                        pg_size_pretty(chunk_size) as size_pretty,
                        chunk_size,
                        is_compressed,
                        compression_status
                    FROM timescaledb_information.chunks
                    WHERE hypertable_schema = 'public'
                    ORDER BY chunk_size DESC
                """
                
                chunks = await conn.fetch(chunk_info_query)
                
                # Optimize large uncompressed chunks
                large_chunks = [c for c in chunks if c['chunk_size'] > 100 * 1024 * 1024 and not c['is_compressed']]
                
                for chunk in large_chunks:
                    try:
                        # Compress large chunks
                        compress_query = f"SELECT compress_chunk('{chunk['chunk_name']}')"
                        await conn.execute(compress_query)
                        optimized_chunks.append(f"Compressed {chunk['chunk_name']}")
                        
                        logger.info("Compressed chunk",
                                   chunk=chunk['chunk_name'],
                                   size=chunk['size_pretty'])
                    except Exception as e:
                        logger.warning("Failed to compress chunk",
                                     chunk=chunk['chunk_name'],
                                     error=str(e))
                
                # Drop old chunks that should be archived
                old_chunks_query = """
                    SELECT chunk_name, hypertable_name, range_end
                    FROM timescaledb_information.chunks
                    WHERE range_end < now() - interval '1 year'
                      AND hypertable_schema = 'public'
                """
                
                old_chunks = await conn.fetch(old_chunks_query)
                
                for chunk in old_chunks:
                    try:
                        # Only drop if archival is confirmed (would need integration with archiver)
                        logger.info("Old chunk candidate for archival",
                                   chunk=chunk['chunk_name'],
                                   age=(datetime.utcnow() - chunk['range_end']).days)
                    except Exception as e:
                        logger.warning("Error processing old chunk",
                                     chunk=chunk['chunk_name'],
                                     error=str(e))
            
            execution_time = time.time() - start_time
            
            return OptimizationResult(
                optimization_type=OptimizationType.CHUNK_OPTIMIZATION,
                success=True,
                message=f"Optimized {len(optimized_chunks)} chunks",
                details={
                    "optimized_chunks": optimized_chunks,
                    "total_chunks": len(chunks),
                    "large_uncompressed_chunks": len(large_chunks),
                    "old_chunks_for_archival": len(old_chunks)
                },
                execution_time_seconds=execution_time,
                performance_impact="high"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return OptimizationResult(
                optimization_type=OptimizationType.CHUNK_OPTIMIZATION,
                success=False,
                message=f"Chunk optimization failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    async def _optimize_compression(self) -> OptimizationResult:
        """Optimize data compression policies"""
        start_time = time.time()
        
        try:
            compression_results = []
            
            async with self.timeseries_manager.get_connection() as conn:
                # Check compression policies
                policies_query = """
                    SELECT hypertable_name, older_than, job_id
                    FROM timescaledb_information.compression_policy
                """
                
                policies = await conn.fetch(policies_query)
                
                # Update compression policies based on data patterns
                for policy in policies:
                    try:
                        # Check if policy needs adjustment based on data age distribution
                        age_distribution_query = f"""
                            SELECT 
                                COUNT(*) as total_chunks,
                                COUNT(*) FILTER (WHERE is_compressed) as compressed_chunks,
                                AVG(chunk_size) as avg_chunk_size
                            FROM timescaledb_information.chunks
                            WHERE hypertable_name = '{policy['hypertable_name']}'
                        """
                        
                        stats = await conn.fetchrow(age_distribution_query)
                        
                        compression_ratio = stats['compressed_chunks'] / stats['total_chunks'] if stats['total_chunks'] > 0 else 0
                        
                        compression_results.append({
                            'hypertable': policy['hypertable_name'],
                            'compression_ratio': compression_ratio,
                            'avg_chunk_size_mb': (stats['avg_chunk_size'] or 0) / 1024 / 1024
                        })
                        
                    except Exception as e:
                        logger.warning("Failed to analyze compression policy",
                                     hypertable=policy['hypertable_name'],
                                     error=str(e))
            
            execution_time = time.time() - start_time
            
            return OptimizationResult(
                optimization_type=OptimizationType.COMPRESSION,
                success=True,
                message=f"Analyzed compression for {len(policies)} hypertables",
                details={
                    "compression_analysis": compression_results,
                    "total_policies": len(policies)
                },
                execution_time_seconds=execution_time,
                performance_impact="medium"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return OptimizationResult(
                optimization_type=OptimizationType.COMPRESSION,
                success=False,
                message=f"Compression optimization failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    async def _refresh_continuous_aggregates(self) -> OptimizationResult:
        """Refresh continuous aggregates for better query performance"""
        start_time = time.time()
        
        try:
            refreshed_aggregates = []
            
            async with self.timeseries_manager.get_connection() as conn:
                # Get continuous aggregates that need refresh
                cagg_query = """
                    SELECT materialization_hypertable_name, view_name
                    FROM timescaledb_information.continuous_aggregates
                """
                
                caggs = await conn.fetch(cagg_query)
                
                for cagg in caggs:
                    try:
                        # Refresh continuous aggregate
                        refresh_query = f"CALL refresh_continuous_aggregate('{cagg['view_name']}', NULL, NULL)"
                        await conn.execute(refresh_query)
                        refreshed_aggregates.append(cagg['view_name'])
                        
                        logger.info("Refreshed continuous aggregate", view=cagg['view_name'])
                        
                    except Exception as e:
                        logger.warning("Failed to refresh continuous aggregate",
                                     view=cagg['view_name'],
                                     error=str(e))
            
            execution_time = time.time() - start_time
            
            return OptimizationResult(
                optimization_type=OptimizationType.CONTINUOUS_AGGREGATES,
                success=True,
                message=f"Refreshed {len(refreshed_aggregates)} continuous aggregates",
                details={
                    "refreshed_aggregates": refreshed_aggregates,
                    "total_aggregates": len(caggs)
                },
                execution_time_seconds=execution_time,
                performance_impact="high"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return OptimizationResult(
                optimization_type=OptimizationType.CONTINUOUS_AGGREGATES,
                success=False,
                message=f"Continuous aggregate refresh failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    async def _collect_performance_stats(self) -> Dict[str, Any]:
        """Collect comprehensive performance statistics"""
        try:
            stats = {}
            
            async with self.db_manager.get_connection() as conn:
                # Database size and connections
                db_stats_query = """
                    SELECT 
                        pg_database_size(current_database()) as db_size,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
                """
                db_stats = await conn.fetchrow(db_stats_query)
                
                # Cache hit ratios
                cache_stats_query = """
                    SELECT 
                        sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as buffer_cache_hit_ratio,
                        sum(idx_blks_hit) / (sum(idx_blks_hit) + sum(idx_blks_read)) as index_cache_hit_ratio
                    FROM pg_statio_user_tables
                """
                cache_stats = await conn.fetchrow(cache_stats_query)
                
                # Table and index statistics
                table_stats_query = """
                    SELECT 
                        COUNT(*) as total_tables,
                        SUM(n_tup_ins + n_tup_upd + n_tup_del) as total_dml_operations,
                        AVG(n_dead_tup::float / GREATEST(n_live_tup, 1)) as avg_dead_tuple_ratio
                    FROM pg_stat_user_tables
                """
                table_stats = await conn.fetchrow(table_stats_query)
                
                stats.update({
                    'database_size_mb': round((db_stats['db_size'] or 0) / 1024 / 1024, 2),
                    'active_connections': db_stats['active_connections'],
                    'connection_usage_percent': round((db_stats['active_connections'] / db_stats['max_connections']) * 100, 2),
                    'buffer_cache_hit_ratio': round((cache_stats['buffer_cache_hit_ratio'] or 0) * 100, 2),
                    'index_cache_hit_ratio': round((cache_stats['index_cache_hit_ratio'] or 0) * 100, 2),
                    'total_tables': table_stats['total_tables'],
                    'total_dml_operations': table_stats['total_dml_operations'],
                    'avg_dead_tuple_ratio': round((table_stats['avg_dead_tuple_ratio'] or 0) * 100, 2)
                })
            
            # TimescaleDB specific stats
            try:
                async with self.timeseries_manager.get_connection() as conn:
                    ts_stats_query = """
                        SELECT 
                            COUNT(*) as total_hypertables,
                            SUM(num_chunks) as total_chunks,
                            COUNT(*) FILTER (WHERE compression_enabled) as compressed_hypertables
                        FROM timescaledb_information.hypertable
                    """
                    ts_stats = await conn.fetchrow(ts_stats_query)
                    
                    stats.update({
                        'total_hypertables': ts_stats['total_hypertables'],
                        'total_chunks': ts_stats['total_chunks'],
                        'compressed_hypertables': ts_stats['compressed_hypertables']
                    })
                    
            except Exception as e:
                logger.warning("Failed to collect TimescaleDB stats", error=str(e))
            
            return stats
            
        except Exception as e:
            logger.error("Failed to collect performance stats", error=str(e))
            return {}
    
    async def _generate_recommendations(self, results: List[OptimizationResult], 
                                      performance_stats: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on results and performance stats"""
        recommendations = []
        
        # Analyze performance stats for recommendations
        if performance_stats.get('buffer_cache_hit_ratio', 100) < 90:
            recommendations.append("Consider increasing shared_buffers - buffer cache hit ratio is low")
        
        if performance_stats.get('connection_usage_percent', 0) > 80:
            recommendations.append("High connection usage detected - consider connection pooling")
        
        if performance_stats.get('avg_dead_tuple_ratio', 0) > 10:
            recommendations.append("High dead tuple ratio - increase vacuum frequency")
        
        # Analyze optimization results
        failed_optimizations = [r for r in results if not r.success]
        if failed_optimizations:
            recommendations.append(f"{len(failed_optimizations)} optimizations failed - check logs for details")
        
        # TimescaleDB specific recommendations
        if performance_stats.get('total_chunks', 0) > performance_stats.get('compressed_hypertables', 0) * 100:
            recommendations.append("Consider enabling compression on more hypertables")
        
        if not recommendations:
            recommendations.append("All performance metrics are within acceptable ranges")
        
        return recommendations
    
    def _is_optimization_needed(self, optimization_type: OptimizationType) -> bool:
        """Check if optimization is needed based on schedule"""
        if optimization_type not in self.last_optimization_times:
            return True
        
        last_run = self.last_optimization_times[optimization_type]
        schedule_interval = self.optimization_schedule.get(optimization_type, timedelta(days=1))
        
        return datetime.utcnow() - last_run >= schedule_interval
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status and history"""
        return {
            'active_optimizations': len(self.active_optimizations),
            'last_optimization_times': {
                opt_type.value: last_time.isoformat() if last_time else None
                for opt_type, last_time in self.last_optimization_times.items()
            },
            'recent_results': [r.to_dict() for r in self.optimization_history[-10:]],
            'performance_thresholds': self.performance_thresholds
        }


# Export main components
__all__ = ['DataOptimizer', 'OptimizationType', 'OptimizationResult', 'OptimizationPriority']