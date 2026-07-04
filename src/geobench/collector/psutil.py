"""psutil collector module."""

import psutil

from . import Collector

import logging

logger = logging.getLogger(__name__)


class PsutilsCollector(Collector):
    """Collector for system metrics via psutil."""

    def __init__(self, config: dict | None = None):
        """Initialize psutil collector."""
        super().__init__(config)

        try:
            psutil.cpu_percent()
            psutil.virtual_memory()

        except Exception as err:
            logger.warning("Failed to initialize psutil collector: %s", err)
            raise RuntimeError("Cannot initialize psutil")

    def read_metrics(self) -> dict:
        """Read current system metrics using psutil.

        Returns:
            Dictionary containing system metrics.
        """
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
            return {}
