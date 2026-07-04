"""Metrics monitoring module with support for multiple metric readers."""

import psutil
from abc import ABC, abstractmethod
from typing import Optional, Dict, List

import logging

logger = logging.getLogger(__name__)


class MetricsReader(ABC):
    """Abstract base class for metrics readers."""

    def __init__(self, reader_type: str = "internal"):
        """Initialize metrics reader.

        Args:
            reader_type: Type of metrics reader - 'internal' for local system sensors
                        or 'external' for remote API readers
        """
        self.available = False
        self.reader_type = reader_type
        self.reader_name = self.__class__.__name__

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
        """Check if this metrics reader is available on the current system.

        Returns:
            True if the metrics reader can be used, False otherwise.
        """
        pass


class PsutilsReader(MetricsReader):
    """Reader for system metrics via psutil."""

    def __init__(self):
        """Initialize psutil reader."""
        super().__init__(reader_type="internal")
        self._init_reader()

    @staticmethod
    def is_available() -> bool:
        """Check if psutil is available.

        Returns:
            True (psutil is always available).
        """
        return True

    def _init_reader(self):
        """Initialize psutil reader."""
        try:
            # Test if psutil works
            psutil.cpu_percent()
            psutil.virtual_memory()
            self.available = True
            logger.info("Psutil metrics reader initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize psutil reader: {e}")
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

        except Exception as e:
            logger.error(f"Error reading psutil metrics: {e}")
            return None


def get_metrics_readers_for_source(source_config: dict) -> List[MetricsReader]:
    """Factory function to get appropriate metrics readers for a data source.

    Args:
        source_config: Data source configuration dictionary with:
            - name: Source identifier
            - interval: Collection interval
            - metrics: List of metric configurations. Each metric can be:
                * Simple string: 'psutils' or 'energy'
                * Dict with 'type' and optional 'config': {'type': 'smart_plug', 'config': {...}}
                * Legacy dict format: {'smart_plug': {...}} (deprecated, for backward compatibility)

    Returns:
        List of initialized MetricsReader instances for this source.
    """
    from .energy import get_energy_reader, HTTPAPIReader

    readers = []
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
                f"[{source_config.get('name')}] Invalid metric format: {metric}"
            )
            continue

        # Process metric based on type
        if metric_type == "psutils":
            if PsutilsReader.is_available():
                reader = PsutilsReader()
                readers.append(reader)
                logger.debug(f"[{source_config.get('name')}] Psutils reader enabled")

        elif metric_type == "energy":
            # Get internal energy readers only
            energy_readers = get_energy_reader()
            readers.extend(energy_readers)
            if energy_readers:
                logger.debug(
                    f"[{source_config.get('name')}] Energy readers enabled: {len(energy_readers)}"
                )

        elif metric_type == "smart_plug":
            # External smart plug reader
            api_url = metric_config.get("api_url", "")
            timeout = metric_config.get("timeout", 1.0)

            if HTTPAPIReader.is_available() and api_url:
                reader = HTTPAPIReader(api_url, timeout)
                if reader.available:
                    readers.append(reader)
                    logger.info(
                        f"[{source_config.get('name')}] Smart plug reader enabled at {api_url}"
                    )
            else:
                logger.warning(
                    f"[{source_config.get('name')}] Smart plug reader not available or missing api_url"
                )

        else:
            logger.warning(
                f"[{source_config.get('name')}] Unknown metric type: {metric_type}"
            )

    return readers
