"""Metrics monitoring module."""
import platform

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
    metrics_config = source_config.get("metrics", [])

    for metric in metrics_config:
        if isinstance(metric, str):
            # Simple string format: 'psutil', 'energy', etc.
            metric_type = metric
            metric_config = {}

        elif isinstance(metric, dict):
            # New format with explicit 'type' key
            if "type" in metric:
                metric_type = metric["type"]
                metric_config = metric.get("config", {})
        else:
            logger.warning(
                "[%s] Invalid metric format: %s", source_config.get("name"), metric
            )
            continue

        # Process metric based on type
        if metric_type == "psutil":
            if PsutilsCollector.is_available():
                collector = PsutilsCollector()
                collectors.append(collector)
                logger.debug(
                    "[%s] Psutils collector enabled", source_config.get("name")
                )

        elif metric_type == "energy":
            energy_collectors = get_energy_collectors()
            collectors.extend(energy_collectors)
            if energy_collectors:
                logger.debug(
                    "[%s] Energy collectors enabled: %d.",
                    source_config.get("name"),
                    len(energy_collectors),
                )

        else:
            logger.warning(
                "[%s] Unknown metric type: %s", source_config.get("name"), metric_type
            )

    return collectors


def get_energy_collectors() -> list[Collector]:
    """Factory function to get the appropriate energy collectors for the current system.

    This function detects the operating system and available energy monitoring
    sensors, then returns a list of appropriate energy collector instances.

    Priority order for collectors:
    1. RAPL (Linux with Intel CPUs)
    2. PowerMetrics (macOS)

    Returns:
        List[Collector]: List of energy collector instances.
    """
    system = platform.system()
    logger.debug("Detecting energy collectors for %s", system)

    collectors = []

    if RAPLCollector.is_available():
        logger.debug("Adding RAPL energy collector")
        collectors.append(RAPLCollector())

    elif PowerMetricsCollector.is_available():
        logger.debug("Adding PowerMetrics energy collector")
        collectors.append(PowerMetricsCollector())

    return collectors
