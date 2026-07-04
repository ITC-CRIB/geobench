"""Metrics monitoring module."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List

import psutil

import logging

logger = logging.getLogger(__name__)


class Collector(ABC):
    """Abstract base class for metrics collectors."""

    def __init__(self):
        """Initialize metrics collector."""
        self.available = False
        self.collector_name = self.__class__.__name__

    @abstractmethod
    def read_metrics(self) -> Optional[Dict]:
        """Read current metrics.

        Returns:
            Dictionary containing metric readings, or None if not available.
        """
        pass

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """Check if this metrics collector is available on the current system.

        Returns:
            True if the metrics collector can be used, False otherwise.
        """
        pass


class PsutilsCollector(Collector):
    """Collector for system metrics via psutil."""

    def __init__(self):
        """Initialize psutil collector."""
        super().__init__()
        self._init_collector()

    @staticmethod
    def is_available() -> bool:
        """Check if psutil is available.

        Returns:
            True (psutil is always available).
        """
        return True

    def _init_collector(self):
        """Initialize psutil collector."""
        try:
            # Test if psutil works
            psutil.cpu_percent()
            psutil.virtual_memory()
            self.available = True
            logger.debug("Psutil metrics collector initialized")
        except Exception as err:
            logger.warning("Failed to initialize psutil collector: %s", err)
            self.available = False

    def read_metrics(self) -> Optional[Dict]:
        """Read current system metrics using psutil.

        Returns:
            Dictionary containing system metrics, or None if not available.
        """
        if not self.available:
            return None

        metrics = {}

        try:
            # CPU metrics
            metrics["cpu_percent"] = psutil.cpu_percent(percpu=True)

            # Memory metrics
            metrics["memory_usage"] = psutil.virtual_memory()._asdict()

            # Network I/O
            try:
                net_io = psutil.net_io_counters()
                metrics["net_bytes_sent"] = net_io.bytes_sent
                metrics["net_bytes_recv"] = net_io.bytes_recv
            except (psutil.AccessDenied, AttributeError):
                metrics["net_bytes_sent"] = 0
                metrics["net_bytes_recv"] = 0

            # Disk I/O
            try:
                disk_io = psutil.disk_io_counters()
                metrics["disk_bytes_read"] = disk_io.read_bytes
                metrics["disk_bytes_write"] = disk_io.write_bytes
            except (psutil.AccessDenied, AttributeError):
                metrics["disk_bytes_read"] = 0
                metrics["disk_bytes_write"] = 0

            return metrics

        except Exception as err:
            logger.error("Error reading psutil metrics: %s", err)
            return None


def get_collectors_for_source(source_config: dict) -> List[Collector]:
    """Factory function to get appropriate metrics collectors for a data source.

    Args:
        source_config: Data source configuration dictionary with:
            - name: Source identifier
            - interval: Collection interval
            - metrics: List of metric configurations. Each metric can be:
                * Simple string: 'psutils' or 'energy'
                * Dict with 'type' and optional 'config': {'type': 'psutils', 'config': {...}}

    Returns:
        List of initialized Collector instances for this source.
    """
    from .energy import get_energy_collector

    collectors = []
    metrics_config = source_config.get("metrics", [])

    for metric in metrics_config:
        if isinstance(metric, str):
            # Simple string format: 'psutils', 'energy', etc.
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
        if metric_type == "psutils":
            if PsutilsCollector.is_available():
                collector = PsutilsCollector()
                collectors.append(collector)
                logger.debug("[%s] Psutils collector enabled", source_config.get("name"))

        elif metric_type == "energy":
            energy_collectors = get_energy_collector()
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
