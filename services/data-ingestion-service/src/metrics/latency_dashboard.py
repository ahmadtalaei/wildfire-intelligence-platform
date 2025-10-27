"""
Challenge 1 Deliverable: Latency & Fidelity Metrics Dashboard
Visualization of data processing latency across ingestion modes and fidelity checks
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json
from dataclasses import dataclass, asdict
import statistics

@dataclass
class LatencyMetrics:
    """Metrics for tracking data ingestion latency and fidelity"""

    source_type: str
    ingestion_mode: str  # 'batch', 'real-time', 'streaming'
    start_time: float
    end_time: float
    latency_ms: float
    record_count: int
    success_count: int
    error_count: int
    fidelity_score: float  # 0.0 to 1.0
    validation_errors: List[str]
    timestamp: str

class LatencyFidelityDashboard:
    """Dashboard for monitoring ingestion latency and data fidelity across all modes"""

    def __init__(self):
        self.metrics_history: List[LatencyMetrics] = []
        self.real_time_metrics: Dict[str, List[float]] = {}

    def record_ingestion_start(self, source_type: str, ingestion_mode: str) -> float:
        """Record the start of a data ingestion operation"""
        start_time = time.time()
        print(f"📊 LATENCY TRACKING: Started {ingestion_mode} ingestion for {source_type}")
        return start_time

    def record_ingestion_complete(self,
                                 source_type: str,
                                 ingestion_mode: str,
                                 start_time: float,
                                 record_count: int,
                                 success_count: int,
                                 validation_results: Dict[str, Any]) -> LatencyMetrics:
        """Record completion of data ingestion and calculate metrics"""

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        error_count = record_count - success_count

        # Calculate fidelity score based on validation results
        fidelity_score = self._calculate_fidelity_score(validation_results, success_count, record_count)

        # Extract validation errors
        validation_errors = validation_results.get('errors', [])

        metrics = LatencyMetrics(
            source_type=source_type,
            ingestion_mode=ingestion_mode,
            start_time=start_time,
            end_time=end_time,
            latency_ms=latency_ms,
            record_count=record_count,
            success_count=success_count,
            error_count=error_count,
            fidelity_score=fidelity_score,
            validation_errors=validation_errors,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self.metrics_history.append(metrics)
        self._update_real_time_metrics(ingestion_mode, latency_ms)

        # Print immediate feedback
        print(f"✅ LATENCY METRICS: {source_type} ({ingestion_mode})")
        print(f"   ⏱️  Latency: {latency_ms:.2f}ms")
        print(f"   📊 Records: {success_count}/{record_count} successful")
        print(f"   🎯 Fidelity: {fidelity_score:.2%}")
        if validation_errors:
            print(f"   ⚠️  Validation Errors: {len(validation_errors)}")

        return metrics

    def _calculate_fidelity_score(self, validation_results: Dict[str, Any],
                                 success_count: int, record_count: int) -> float:
        """Calculate data fidelity score based on validation results"""
        if record_count == 0:
            return 0.0

        # Base score from successful records
        base_score = success_count / record_count

        # Adjust for validation quality
        schema_valid = validation_results.get('schema_valid', 0)
        format_valid = validation_results.get('format_valid', 0)
        completeness = validation_results.get('completeness', 0)

        if success_count > 0:
            # Quality adjustments (weighted)
            quality_score = (
                (schema_valid / success_count) * 0.4 +
                (format_valid / success_count) * 0.3 +
                (completeness / success_count) * 0.3
            )
            return base_score * quality_score

        return base_score

    def _update_real_time_metrics(self, ingestion_mode: str, latency_ms: float):
        """Update real-time rolling metrics"""
        if ingestion_mode not in self.real_time_metrics:
            self.real_time_metrics[ingestion_mode] = []

        self.real_time_metrics[ingestion_mode].append(latency_ms)

        # Keep only last 100 measurements for rolling averages
        if len(self.real_time_metrics[ingestion_mode]) > 100:
            self.real_time_metrics[ingestion_mode] = self.real_time_metrics[ingestion_mode][-100:]

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard summary"""

        if not self.metrics_history:
            return {"status": "No metrics available yet"}

        # Overall statistics
        total_records = sum(m.record_count for m in self.metrics_history)
        total_successful = sum(m.success_count for m in self.metrics_history)
        avg_fidelity = statistics.mean([m.fidelity_score for m in self.metrics_history])

        # Latency by ingestion mode
        latency_by_mode = {}
        for mode in ['batch', 'real-time', 'streaming']:
            mode_metrics = [m for m in self.metrics_history if m.ingestion_mode == mode]
            if mode_metrics:
                latencies = [m.latency_ms for m in mode_metrics]
                latency_by_mode[mode] = {
                    'avg_latency_ms': statistics.mean(latencies),
                    'min_latency_ms': min(latencies),
                    'max_latency_ms': max(latencies),
                    'median_latency_ms': statistics.median(latencies),
                    'operations_count': len(latencies)
                }

        # Source type performance
        source_performance = {}
        for metrics in self.metrics_history:
            source = metrics.source_type
            if source not in source_performance:
                source_performance[source] = {
                    'total_records': 0,
                    'successful_records': 0,
                    'avg_latency_ms': 0,
                    'avg_fidelity': 0,
                    'operations': 0
                }

            perf = source_performance[source]
            perf['total_records'] += metrics.record_count
            perf['successful_records'] += metrics.success_count
            perf['avg_latency_ms'] += metrics.latency_ms
            perf['avg_fidelity'] += metrics.fidelity_score
            perf['operations'] += 1

        # Calculate averages
        for source, perf in source_performance.items():
            if perf['operations'] > 0:
                perf['avg_latency_ms'] /= perf['operations']
                perf['avg_fidelity'] /= perf['operations']
                perf['success_rate'] = perf['successful_records'] / perf['total_records'] if perf['total_records'] > 0 else 0

        return {
            'dashboard_generated_at': datetime.now(timezone.utc).isoformat(),
            'overall_statistics': {
                'total_operations': len(self.metrics_history),
                'total_records_processed': total_records,
                'total_successful_records': total_successful,
                'overall_success_rate': total_successful / total_records if total_records > 0 else 0,
                'average_fidelity_score': avg_fidelity
            },
            'latency_by_ingestion_mode': latency_by_mode,
            'performance_by_source_type': source_performance,
            'real_time_rolling_averages': {
                mode: {
                    'current_avg_latency_ms': statistics.mean(latencies) if latencies else 0,
                    'samples_count': len(latencies)
                }
                for mode, latencies in self.real_time_metrics.items()
            }
        }

    def print_dashboard(self):
        """Print formatted dashboard to console"""
        summary = self.get_dashboard_summary()

        print("\n" + "="*80)
        print("📊 CHALLENGE 1: LATENCY & FIDELITY METRICS DASHBOARD")
        print("="*80)

        if 'overall_statistics' not in summary:
            print("No metrics data available yet.")
            return

        stats = summary['overall_statistics']
        print(f"📈 OVERALL PERFORMANCE:")
        print(f"   Operations: {stats['total_operations']}")
        print(f"   Records Processed: {stats['total_records_processed']:,}")
        print(f"   Success Rate: {stats['overall_success_rate']:.2%}")
        print(f"   Average Fidelity: {stats['average_fidelity_score']:.2%}")

        print(f"\n⏱️  LATENCY BY INGESTION MODE:")
        for mode, metrics in summary['latency_by_ingestion_mode'].items():
            print(f"   {mode.upper()}:")
            print(f"     Average: {metrics['avg_latency_ms']:.2f}ms")
            print(f"     Range: {metrics['min_latency_ms']:.2f}ms - {metrics['max_latency_ms']:.2f}ms")
            print(f"     Operations: {metrics['operations_count']}")

        print(f"\n🎯 PERFORMANCE BY SOURCE TYPE:")
        for source, perf in summary['performance_by_source_type'].items():
            print(f"   {source.upper()}:")
            print(f"     Success Rate: {perf['success_rate']:.2%}")
            print(f"     Avg Latency: {perf['avg_latency_ms']:.2f}ms")
            print(f"     Avg Fidelity: {perf['avg_fidelity']:.2%}")
            print(f"     Records: {perf['successful_records']:,}/{perf['total_records']:,}")

        print("="*80)

    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        export_data = {
            'metrics_history': [asdict(m) for m in self.metrics_history],
            'dashboard_summary': self.get_dashboard_summary()
        }

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"📄 Metrics exported to: {filepath}")

# Global dashboard instance for the ingestion service
dashboard = LatencyFidelityDashboard()

def get_dashboard() -> LatencyFidelityDashboard:
    """Get the global dashboard instance"""
    return dashboard