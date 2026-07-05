"""psutil collector module."""

import psutil

from . import Collector, CollectorInfo

import logging

logger = logging.getLogger(__name__)


class PsutilsCollector(Collector):
    """Collector for system metrics via psutil."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="psutil",
            name="psutil Collector",
            description="CPU, memory, IO, and network metrics using psutil.",
        )

    def __init__(self, config: dict | None = None):
        """Initialize psutil collector.

        Raises:
            RuntimeError: If cannot initialize the collector.
        """
        super().__init__(config)

        try:
            psutil.cpu_percent()
            psutil.virtual_memory()

        except Exception as err:
            logger.warning("Failed to initialize psutil collector: %s", err)
            raise RuntimeError("Cannot initialize psutil")

    def read_metrics(self) -> dict:
        """Read system metrics using psutil.

        Returns:
            Dictionary containing system metrics.
        """
        out = {}

        try:
            # CPU metrics
            out["cpu_percent"] = psutil.cpu_percent(percpu=True)

            # Memory metrics
            out["memory_usage"] = psutil.virtual_memory()._asdict()

            # Network I/O
            try:
                net_io = psutil.net_io_counters()
                out["net_bytes_sent"] = net_io.bytes_sent
                out["net_bytes_recv"] = net_io.bytes_recv
            except (psutil.AccessDenied, AttributeError):
                out["net_bytes_sent"] = 0
                out["net_bytes_recv"] = 0

            # Disk I/O
            try:
                disk_io = psutil.disk_io_counters()
                out["disk_bytes_read"] = disk_io.read_bytes
                out["disk_bytes_write"] = disk_io.write_bytes
            except (psutil.AccessDenied, AttributeError):
                out["disk_bytes_read"] = 0
                out["disk_bytes_write"] = 0

            return out

        except Exception as err:
            logger.error("Error reading psutil metrics: %s", err)
            return {}
