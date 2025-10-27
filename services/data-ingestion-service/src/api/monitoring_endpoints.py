"""
Monitoring API Endpoints for Critical Alerts and Buffering
Provides health checks, metrics, and management endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from ..streaming.critical_alert_handler import CriticalAlertHandler
from ..streaming.buffer_manager import get_buffer_manager
from ..streaming.stream_manager import StreamManager

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

# Global instances (initialized by main app)
critical_handler: Optional[CriticalAlertHandler] = None
stream_manager: Optional[StreamManager] = None


def set_monitoring_instances(
    handler: CriticalAlertHandler,
    manager: StreamManager
):
    """Set global instances for monitoring"""
    global critical_handler, stream_manager
    critical_handler = handler
    stream_manager = manager


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check for all components"""
    buffer_manager = get_buffer_manager()

    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }

    # Check critical alert handler
    if critical_handler:
        handler_healthy = critical_handler.is_healthy()
        health_status['components']['critical_alerts'] = {
            'healthy': handler_healthy,
            'is_running': critical_handler.is_running,
            'connections_active': critical_handler.metrics.get('connections_active', 0),
            'last_alert_time': critical_handler.metrics.get('last_alert_time')
        }
        if not handler_healthy:
            health_status['status'] = 'degraded'
    else:
        health_status['components']['critical_alerts'] = {
            'healthy': False,
            'error': 'Handler not initialized'
        }
        health_status['status'] = 'degraded'

    # Check buffer manager
    buffer_healthy = buffer_manager.is_healthy()
    buffer_metrics = buffer_manager.get_all_metrics()
    health_status['components']['buffer_manager'] = {
        'healthy': buffer_healthy,
        'total_buffers': buffer_metrics['global']['total_buffers'],
        'total_messages': buffer_metrics['global']['total_buffer_size'],
        'last_check': buffer_metrics['global']['last_health_check']
    }
    if not buffer_healthy:
        health_status['status'] = 'degraded'

    # Check stream manager
    if stream_manager:
        stream_metrics = await stream_manager.get_metrics()
        health_status['components']['stream_manager'] = {
            'healthy': True,  # Assume healthy if running
            'active_streams': stream_metrics.get('active_streams', 0),
            'total_throughput': stream_metrics.get('total_throughput', 0)
        }
    else:
        health_status['components']['stream_manager'] = {
            'healthy': False,
            'error': 'Manager not initialized'
        }
        health_status['status'] = 'degraded'

    # Overall status
    if health_status['status'] == 'degraded':
        health_status['message'] = 'One or more components are unhealthy'
    else:
        health_status['message'] = 'All components are healthy'

    return health_status


@router.get("/metrics/critical-alerts")
async def get_critical_alert_metrics() -> Dict[str, Any]:
    """Get metrics for critical alert handling"""
    if not critical_handler:
        raise HTTPException(status_code=503, detail="Critical alert handler not initialized")

    metrics = critical_handler.get_metrics()

    return {
        'timestamp': datetime.now().isoformat(),
        'alerts': {
            'sent': metrics.get('alerts_sent', 0),
            'failed': metrics.get('alerts_failed', 0),
            'success_rate': metrics['alerts_sent'] / (metrics['alerts_sent'] + metrics['alerts_failed'])
                          if (metrics['alerts_sent'] + metrics['alerts_failed']) > 0 else 0
        },
        'latency': {
            'avg_ms': metrics.get('avg_latency_ms', 0),
            'max_ms': metrics.get('max_latency_ms', 0),
            'min_ms': metrics.get('min_latency_ms', float('inf')),
            'percentiles': metrics.get('latency_percentiles', {})
        },
        'connections': {
            'active': metrics.get('connections_active', 0),
            'reconnections': metrics.get('reconnection_count', 0),
            'last_alert': metrics.get('last_alert_time')
        }
    }


@router.get("/metrics/buffers")
async def get_buffer_metrics() -> Dict[str, Any]:
    """Get metrics for all offline buffers"""
    buffer_manager = get_buffer_manager()
    metrics = buffer_manager.get_all_metrics()

    return {
        'timestamp': datetime.now().isoformat(),
        'global': metrics['global'],
        'buffers': [
            {
                'buffer_id': buffer_id,
                'connector_type': buffer_manager.buffers[buffer_id].config.connector_type,
                'metrics': buffer_metrics
            }
            for buffer_id, buffer_metrics in metrics['buffers'].items()
        ]
    }


@router.get("/metrics/buffers/{buffer_id}")
async def get_buffer_metrics_by_id(buffer_id: str) -> Dict[str, Any]:
    """Get metrics for a specific buffer"""
    buffer_manager = get_buffer_manager()
    metrics = buffer_manager.get_buffer_metrics(buffer_id)

    if not metrics:
        raise HTTPException(status_code=404, detail=f"Buffer {buffer_id} not found")

    return {
        'timestamp': datetime.now().isoformat(),
        'buffer_id': buffer_id,
        'metrics': metrics
    }


@router.get("/metrics/streams")
async def get_stream_metrics() -> Dict[str, Any]:
    """Get metrics for all active streams"""
    if not stream_manager:
        raise HTTPException(status_code=503, detail="Stream manager not initialized")

    metrics = await stream_manager.get_metrics()

    return {
        'timestamp': datetime.now().isoformat(),
        'streams': metrics
    }


@router.post("/buffers/{buffer_id}/flush")
async def flush_buffer(buffer_id: str, batch_size: Optional[int] = None) -> Dict[str, Any]:
    """Manually flush a specific buffer"""
    buffer_manager = get_buffer_manager()

    try:
        flushed_count = await buffer_manager.flush_buffer(buffer_id, batch_size)

        return {
            'success': True,
            'buffer_id': buffer_id,
            'messages_flushed': flushed_count,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(
            "Failed to flush buffer",
            buffer_id=buffer_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buffers/flush-all")
async def flush_all_buffers(priority_only: bool = False) -> Dict[str, Any]:
    """Flush all buffers"""
    buffer_manager = get_buffer_manager()

    try:
        results = await buffer_manager.flush_all_buffers(priority_only=priority_only)

        return {
            'success': True,
            'results': results,
            'total_flushed': sum(results.values()),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(
            "Failed to flush buffers",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/critical-alerts/test")
async def test_critical_alert() -> Dict[str, Any]:
    """Send a test critical alert"""
    if not critical_handler:
        raise HTTPException(status_code=503, detail="Critical alert handler not initialized")

    test_alert = {
        'alert_type': 'TEST_ALERT',
        'severity': 'INFO',
        'message': 'This is a test critical alert',
        'timestamp': datetime.now().isoformat(),
        'test': True
    }

    try:
        success = await critical_handler.send_critical_alert(
            test_alert,
            source_id="monitoring_test"
        )

        return {
            'success': success,
            'alert': test_alert,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(
            "Failed to send test alert",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_configuration() -> Dict[str, Any]:
    """Get current configuration for monitoring"""
    buffer_manager = get_buffer_manager()

    config = {
        'timestamp': datetime.now().isoformat(),
        'critical_alerts': {},
        'buffering': {},
        'streaming': {}
    }

    # Critical alert config
    if critical_handler:
        config['critical_alerts'] = {
            'enabled': True,
            'max_latency_ms': critical_handler.max_latency_ms,
            'heartbeat_interval': critical_handler.heartbeat_interval,
            'kafka_topic': critical_handler.alert_topic
        }
    else:
        config['critical_alerts']['enabled'] = False

    # Buffer config
    config['buffering'] = {
        'enabled': True,
        'buffer_dir': str(buffer_manager.buffer_dir),
        'total_buffers': len(buffer_manager.buffers)
    }

    # Stream config
    if stream_manager:
        stream_metrics = await stream_manager.get_metrics()
        config['streaming'] = {
            'enabled': True,
            'active_streams': stream_metrics.get('active_streams', 0),
            'max_concurrent': 50  # From config
        }
    else:
        config['streaming']['enabled'] = False

    return config


@router.get("/alerts/recent")
async def get_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent critical alerts (if stored)"""
    # This would require implementing alert storage in CriticalAlertHandler
    # For now, return a placeholder
    return {
        'message': 'Alert history not yet implemented',
        'timestamp': datetime.now().isoformat()
    }


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get overall system status"""
    buffer_manager = get_buffer_manager()

    status = {
        'timestamp': datetime.now().isoformat(),
        'status': 'operational',
        'components': []
    }

    # Critical alerts status
    if critical_handler and critical_handler.is_healthy():
        status['components'].append({
            'name': 'Critical Alerts',
            'status': 'operational',
            'details': f"{critical_handler.metrics['alerts_sent']} alerts sent"
        })
    else:
        status['components'].append({
            'name': 'Critical Alerts',
            'status': 'degraded',
            'details': 'Handler not healthy or not initialized'
        })
        status['status'] = 'degraded'

    # Buffer status
    if buffer_manager.is_healthy():
        metrics = buffer_manager.get_all_metrics()
        status['components'].append({
            'name': 'Buffer Manager',
            'status': 'operational',
            'details': f"{metrics['global']['total_buffers']} buffers, {metrics['global']['total_buffer_size']} messages"
        })
    else:
        status['components'].append({
            'name': 'Buffer Manager',
            'status': 'degraded',
            'details': 'One or more buffers unhealthy'
        })
        status['status'] = 'degraded'

    # Stream manager status
    if stream_manager:
        stream_metrics = await stream_manager.get_metrics()
        status['components'].append({
            'name': 'Stream Manager',
            'status': 'operational',
            'details': f"{stream_metrics.get('active_streams', 0)} active streams"
        })
    else:
        status['components'].append({
            'name': 'Stream Manager',
            'status': 'degraded',
            'details': 'Manager not initialized'
        })
        status['status'] = 'degraded'

    return status


# Prometheus metrics export (if using prometheus_client)
@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Export metrics in Prometheus format"""
    # This would integrate with prometheus_client library
    # For now, return a placeholder
    return {
        'message': 'Prometheus export endpoint',
        'note': 'Integrate with prometheus_client for full implementation',
        'timestamp': datetime.now().isoformat()
    }