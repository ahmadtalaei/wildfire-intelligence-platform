"""
TopicResolver: Automatic Kafka topic mapping and routing
Dynamically routes messages to appropriate topics based on content and source
"""

from typing import Dict, Any, Optional, List
import re
import structlog

logger = structlog.get_logger()


class TopicResolver:
    """
    Resolves Kafka topics based on source patterns, content, and rules
    Supports custom mappings and fallback logic
    """

    def __init__(self, custom_mappings: Optional[Dict[str, str]] = None):
        self.custom_mappings = custom_mappings or {}

        # Default pattern-based mappings
        # ORDER MATTERS: More specific patterns must come BEFORE generic patterns!
        self.pattern_mappings = {
            # NASA FIRMS patterns
            r'^firms_': 'wildfire-nasa-firms',
            r'^landsat_nrt': 'wildfire-nasa-firms',

            # Weather patterns - SPECIFIC FIRST (before generic noaa_)
            r'^noaa_stations': 'wildfire-weather-stations',  # ✅ FIX: Station observations go to dedicated topic
            r'^noaa_alerts': 'wildfire-weather-alerts',      # ✅ FIX: Weather alerts go to dedicated topic
            r'^noaa_': 'wildfire-weather-data',              # Generic NOAA fallback
            r'^wx_': 'wildfire-weather-data',
            r'^weather_': 'wildfire-weather-data',

            # IoT sensor patterns
            r'^iot_': 'wildfire-iot-sensors',
            r'^sensor_': 'wildfire-iot-sensors',

            # Satellite patterns
            r'^sat_': 'wildfire-satellite-data',
            r'^satellite_': 'wildfire-satellite-data',

            # Alert patterns
            r'_alert': 'wildfire-alerts-generated',
            r'_warning': 'wildfire-alerts-generated',
        }

        # Content-based routing rules
        self.content_rules = [
            {
                'field': 'data_type',
                'value': 'satellite_image',
                'topic': 'wildfire-satellite-imagery'
            },
            {
                'field': 'event',
                'pattern': r'(red flag|fire weather)',
                'topic': 'wildfire-weather-alerts'
            },
            {
                'field': 'alert_id',
                'exists': True,
                'topic': 'wildfire-alerts-generated'
            }
        ]

        # Fallback topic
        self.default_topic = 'wildfire-data'

        # Metrics
        self.resolution_count = 0
        self.fallback_count = 0
        self.topic_usage = {}

    def resolve_topic(
        self,
        source_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Resolve Kafka topic for given source and data

        Resolution order:
        1. Custom mappings (exact match)
        2. Content-based rules
        3. Pattern-based matching on source_id
        4. Default fallback topic
        """
        self.resolution_count += 1

        # 1. Check custom mappings
        if source_id in self.custom_mappings:
            topic = self.custom_mappings[source_id]
            self._record_usage(topic)
            logger.debug("Topic resolved via custom mapping", source_id=source_id, topic=topic)
            return topic

        # 2. Check content-based rules (if data provided)
        if data:
            content_topic = self._resolve_by_content(data)
            if content_topic:
                self._record_usage(content_topic)
                logger.debug("Topic resolved via content rules", source_id=source_id, topic=content_topic)
                return content_topic

        # 3. Check pattern-based mappings
        pattern_topic = self._resolve_by_pattern(source_id)
        if pattern_topic:
            self._record_usage(pattern_topic)
            logger.debug("Topic resolved via pattern", source_id=source_id, topic=pattern_topic)
            return pattern_topic

        # 4. Fallback to default
        self.fallback_count += 1
        self._record_usage(self.default_topic)
        logger.warning(
            "Topic resolved to default fallback",
            source_id=source_id,
            default_topic=self.default_topic
        )
        return self.default_topic

    def _resolve_by_content(self, data: Dict[str, Any]) -> Optional[str]:
        """Resolve topic based on data content"""
        for rule in self.content_rules:
            field = rule.get('field')
            if field not in data:
                continue

            field_value = data[field]

            # Check exact value match
            if 'value' in rule and field_value == rule['value']:
                return rule['topic']

            # Check pattern match
            if 'pattern' in rule:
                if isinstance(field_value, str):
                    if re.search(rule['pattern'], field_value, re.IGNORECASE):
                        return rule['topic']

            # Check existence
            if rule.get('exists') and field_value:
                return rule['topic']

        return None

    def _resolve_by_pattern(self, source_id: str) -> Optional[str]:
        """Resolve topic based on source_id pattern"""
        source_lower = source_id.lower()

        for pattern, topic in self.pattern_mappings.items():
            if re.match(pattern, source_lower):
                return topic

        return None

    def _record_usage(self, topic: str):
        """Record topic usage for metrics"""
        self.topic_usage[topic] = self.topic_usage.get(topic, 0) + 1

    def add_custom_mapping(self, source_id: str, topic: str):
        """Add or update custom mapping"""
        self.custom_mappings[source_id] = topic
        logger.info("Custom topic mapping added", source_id=source_id, topic=topic)

    def add_pattern_mapping(self, pattern: str, topic: str):
        """Add new pattern-based mapping"""
        self.pattern_mappings[pattern] = topic
        logger.info("Pattern topic mapping added", pattern=pattern, topic=topic)

    def add_content_rule(self, rule: Dict[str, Any]):
        """Add new content-based routing rule"""
        self.content_rules.append(rule)
        logger.info("Content routing rule added", rule=rule)

    def get_metrics(self) -> Dict[str, Any]:
        """Get topic resolver metrics"""
        return {
            'resolution_count': self.resolution_count,
            'fallback_count': self.fallback_count,
            'fallback_rate': (
                self.fallback_count / self.resolution_count
                if self.resolution_count > 0 else 0.0
            ),
            'topic_usage': self.topic_usage,
            'custom_mappings_count': len(self.custom_mappings),
            'pattern_mappings_count': len(self.pattern_mappings),
            'content_rules_count': len(self.content_rules)
        }

    def get_all_topics(self) -> List[str]:
        """Get list of all possible topics"""
        topics = set()

        # From custom mappings
        topics.update(self.custom_mappings.values())

        # From pattern mappings
        topics.update(self.pattern_mappings.values())

        # From content rules
        for rule in self.content_rules:
            topics.add(rule['topic'])

        # Add default
        topics.add(self.default_topic)

        return sorted(list(topics))
