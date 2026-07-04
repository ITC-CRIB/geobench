"""Metrics monitoring module."""
from .collector import Collector
from .collector.psutil import PsutilsCollector
from .collector.rapl import RAPLCollector
from .collector.powermetrics import PowerMetricsCollector

import logging

logger = logging.getLogger(__name__)


def get_collectors_for_source(source_config: dict) -> list[Collector]:
    """Factory function to get appropriate metrics collectors for a data source.

    Args:
        source_config: Data source configuration dictionary with:
            - name: Source identifier
            - interval: Collection interval
            - metrics: List of metric configurations. Each metric can be:
                * Simple string: 'psutil' or 'energy'
                * Dict with 'type' and optional 'config': {'type': 'psutil', 'config': {...}}

    Returns:
        List of initialized Collector instances for this source.
    """
    collectors = []

    for metric in source_config.get("metrics", []):
        if isinstance(metric, str):
            # Simple string format: 'psutil', 'energy', etc.
            metric_type = metric
            config = {}

        elif isinstance(metric, dict):
            # New format with explicit 'type' key
            if "type" in metric:
                metric_type = metric["type"]
                config = metric.get("config", {})
        else:
            logger.warning(
                "[%s] Invalid metric format: %s", source_config.get("name"), metric
            )
            continue

        # Process metric based on type
        if metric_type == "psutil":
            collectors.append(PsutilsCollector(config))
            logger.debug(
                "[%s] Psutils collector enabled", source_config.get("name")
            )

        elif metric_type == "energy":
            try:
                collectors.append(RAPLCollector(config))
                logger.debug("RAPL energy collector enabled")
            except RuntimeError:
                pass

            try:
                collectors.append(PowerMetricsCollector(config))
                logger.debug("PowerMetrics energy collector enabled")
            except RuntimeError:
                pass

        else:
            logger.warning(
                "[%s] Unknown collector: %s", source_config.get("name"), metric_type
            )

    return collectors
