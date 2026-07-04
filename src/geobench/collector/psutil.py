"""psutil collector module."""

import psutil

from . import Collector

import logging

logger = logging.getLogger(__name__)


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

    def read_metrics(self) -> dict:
        """Read current system metrics using psutil.

        Returns:
            Dictionary containing system metrics.
        """
        if not self.available:
            return {}

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
